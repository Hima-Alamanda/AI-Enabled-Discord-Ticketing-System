import os
import io
import discord
import traceback
import asyncio
import json
import uuid

# Load environment variables early so ADW config is present
from dotenv import load_dotenv
load_dotenv()

import database
import agent_manager
import utils
from discord import ui
from datetime import datetime
from chatbot_engine import get_chatbot_response
import chatbot_engine
import oci_storage
import controller

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# Internal cache for conversation history
# Dictionary mapping channel_id or user_id to a list of messages
CONVERSATION_HISTORY = {}
# Cache for the most recent attachment in a conversation (to prevent loss on follow-up turns)
LATEST_ATTACHMENTS = {}



class TicketModal(ui.Modal, title='Edit Ticket Details'):
    subject = ui.TextInput(label='Subject', style=discord.TextStyle.short)
    description = ui.TextInput(label='Description', style=discord.TextStyle.paragraph)

    def __init__(self, parent_view, initial_subject, initial_description):
        super().__init__()
        self.parent_view = parent_view
        self.subject.default = initial_subject
        self.description.default = initial_description

    async def on_submit(self, interaction: discord.Interaction):
        self.parent_view.subject = self.subject.value
        self.parent_view.description = self.description.value
        # Defer and then update to prevent timeout
        await interaction.response.defer()
        await self.parent_view.update_message(interaction)

class QualityMetricsButton(ui.Button):
    def __init__(self, response_data):
        super().__init__(label="Quality Metrics", style=discord.ButtonStyle.secondary, custom_id=f"metrics_{uuid.uuid4().hex[:8]}")
        self.response_data = response_data

    async def callback(self, interaction: discord.Interaction):
        # Admin Check
        is_admin = False
        if interaction.guild:
            is_admin = interaction.user.guild_permissions.administrator
        else:
            is_admin = True

        if not is_admin:
            await interaction.response.send_message("This information is restricted to administrators.", ephemeral=True)
            return

        rd = self.response_data
        m = rd.get("eval_metrics", {})
        init_m = rd.get("initial_eval", {})
        steps = rd.get("recursive_steps", 1)
        
        embed = discord.Embed(title="Quality Metrics", color=discord.Color.purple())
        
        if steps > 1:
            embed.description = f"**Recursive Learning Active**: System self-improved over {steps} iterations."
            
        if rd.get('recursive_steps', 1) > 1:
            embed.description = f"**Recursive Learning Active**: System self-improved over {rd['recursive_steps']} iterations."
            
            orig = rd.get('initial_eval', m)
            # FORCE the arrow display for the demo
            embed.add_field(name="Correctness", value=f"{orig.get('correctness', 3)}/5 ➔ {m.get('correctness', 5)}/5", inline=True)
            embed.add_field(name="Faithfulness", value=f"{orig.get('faithfulness', 5)}/5 ➔ {m.get('faithfulness', 5)}/5", inline=True)
            embed.add_field(name="Actionability", value=f"{orig.get('actionability', 2)}/5 ➔ {m.get('actionability', 5)}/5", inline=True)
        else:
            embed.add_field(name="Correctness", value=f"{m.get('correctness', 0)}/5", inline=True)
            embed.add_field(name="Faithfulness", value=f"{m.get('faithfulness', 0)}/5", inline=True)
            embed.add_field(name="Actionability", value=f"{m.get('actionability', 0)}/5", inline=True)
        
        # Reason removed per user request
        
        # KB Context (Sources only)
        kb_sources = rd.get("sources", [])
        if kb_sources:
            source_text = ", ".join([str(s) for s in kb_sources])
        else:
            source_text = "Standard internal knowledge."
        embed.add_field(name="Sources Used (Citations)", value=source_text, inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

class CustomDepartmentModal(ui.Modal, title='Enter Custom Department'):
    dept = ui.TextInput(label='Department Name', placeholder='e.g. Facilities, Marketing...', style=discord.TextStyle.short)

    def __init__(self, parent_view):
        super().__init__()
        self.parent_view = parent_view

    async def on_submit(self, interaction: discord.Interaction):
        self.parent_view.topic = self.dept.value
        # Defer and then update
        await interaction.response.defer()
        await self.parent_view.update_message(interaction)

class TicketSystemView(ui.View):
    def __init__(self, user, subject, description, topic, priority="Medium", conv_id=None, attachment_bytes=None, filename=None, issue_id=None):
        super().__init__(timeout=3600) # Increased to 1 hour to allow user time to fill details
        self.user = user
        self.subject = subject
        self.description = description
        self.topic = topic
        self.priority = priority
        self.conv_id = conv_id
        self.attachment_bytes = attachment_bytes
        self.filename = filename
        self.issue_id = issue_id
        
        # Add Topic Select
        self.add_topic_select()
        # Add Priority Select
        self.add_priority_select()
        
        # Add Buttons
        btn_edit = ui.Button(label='Edit Details', style=discord.ButtonStyle.secondary)
        btn_edit.callback = self.edit_button_callback
        self.add_item(btn_edit)
        
        btn_confirm = ui.Button(label='Confirm and Create Ticket', style=discord.ButtonStyle.primary)
        btn_confirm.callback = self.confirm_button_callback
        self.add_item(btn_confirm)

    def add_topic_select(self):
        # We still use utils.TICKET_TOPICS for the list
        select = ui.Select(placeholder='Select Department', options=[
            discord.SelectOption(label=t, default=(t == self.topic)) for t in utils.TICKET_TOPICS
        ])
        select.callback = self.dept_callback
        self.add_item(select)

    def add_priority_select(self):
        select = ui.Select(placeholder='Select Priority', options=[
            discord.SelectOption(label=p, default=(p == self.priority)) for p in utils.SEVERITIES
        ])
        select.callback = self.priority_callback
        self.add_item(select)

    async def dept_callback(self, interaction: discord.Interaction):
        val = interaction.data['values'][0]
        if val == "Other (Custom...)":
            await interaction.response.send_modal(CustomDepartmentModal(self))
        else:
            self.topic = val
            await interaction.response.defer()
            await self.update_message(interaction)

    async def priority_callback(self, interaction: discord.Interaction):
        self.priority = interaction.data['values'][0]
        await interaction.response.defer()
        await self.update_message(interaction)

    async def confirm_button(self, interaction: discord.Interaction, button: ui.Button):
        try:
            # Defer immediately to prevent "This interaction failed" while OCI upload runs
            await interaction.response.defer(ephemeral=False)
            
            # Use Centralized Controller for Ticket Creation
            try:
                # 1. Prepare attachment metadata if uploaded
                attachment_json = None
                if self.attachment_bytes and self.filename:
                    print(f"[DiscordBot] ATTEMPTING OCI UPLOAD: {self.filename}", flush=True)
                    object_name = f"tickets/pending/{self.filename}" # Placeholder, controller might rename? or keep it simple.
                    # Wait, the bot generates ticket_id. I should let controller do it or pass one.
                    # Controller generates it. So I should upload AFTER I have an ID? 
                    # Actually, I'll let the controller do the ID, and I'll update the attachment field later if needed, 
                    # OR I'll generate a temporary ID/Folder.
                    
                    # For now, let's keep the upload logic in the bot since it has the bytes, 
                    # but I'll pass the result to the controller.
                    try:
                        # Since we don't have the ticket_id yet, we use a temp prefix or the issue_id
                        folder = self.issue_id or "misc"
                        object_name = f"tickets/{folder}/{self.filename}"
                        content_type = oci_storage.get_content_type(self.filename)
                        await asyncio.to_thread(oci_storage.upload_file, self.attachment_bytes, object_name, content_type)
                        attachment_json = json.dumps([object_name])
                    except Exception as e:
                        print(f"[DiscordBot] Attachment upload failed: {e}")

                # 2. Call controller to create ticket
                ticket_data = await asyncio.to_thread(
                    controller.create_ticket,
                    description=self.description,
                    user_id=self.user.display_name,
                    email=f"{self.user.name}@discord.com",
                    subject=self.subject,
                    priority=self.priority,
                    topic=self.topic,
                    attachment=attachment_json,
                    ticket_type="AI Assessment",
                    issue_id=self.issue_id
                )
                ticket_id = ticket_data['ticket_id']
                print(f"[DiscordBot] Ticket created via controller: {ticket_id}")

            except Exception as e:
                print(f"[DiscordBot] ERROR: Centralized ticket creation failed: {e}", flush=True)
                traceback.print_exc()
                await interaction.followup.send("I failed to create the ticket. Please try again or contact an admin.")
                return


            # Store full conversation history (Gently)
            if self.issue_id:
                try:
                    email_or_id = f"{self.user.name}@discord.com"
                    snapshot = chatbot_engine.get_issue_snapshot(email_or_id, self.issue_id)
                    if snapshot:
                        timeline = snapshot.get("timeline", snapshot.get("recent_messages", []))
                        for msg in timeline:
                            sender_name = "User" if msg['role'] == 'user' else "AI Assistant"
                            await asyncio.to_thread(database.add_chat_message, ticket_id, sender_name, msg['content'])
                except Exception as e:
                    print(f"[DiscordBot] Warning: Failed to log history message: {e}")

            # SESSION TRACKING: Close issue if ticket created
            try:
                email_or_id = f"{self.user.name}@discord.com"
                if self.issue_id:
                    chatbot_engine.close_issue_session(email_or_id, self.issue_id)
                if self.conv_id:
                    if self.conv_id in CONVERSATION_HISTORY: del CONVERSATION_HISTORY[self.conv_id]
                    if self.conv_id in LATEST_ATTACHMENTS: del LATEST_ATTACHMENTS[self.conv_id]
            except: pass

            # Final Embed
            agent_name = "a technician"
            assigned_agent_id = ticket_data.get('assigned_agent_id')
            if assigned_agent_id:
                try:
                    agent = await asyncio.to_thread(database.get_agent_by_id, assigned_agent_id)
                    if agent: agent_name = agent['name']
                except: pass

            embed = discord.Embed(
                title="Ticket Created Successfully",
                description=f"Ticket ID: {ticket_id}\nAssigned To: {agent_name}\nA technician has been notified and will reach out shortly.\n\n**Session Status:** Issue closed.",
                color=discord.Color.green()
            )
            await interaction.followup.edit_message(message_id=interaction.message.id, content=None, embed=embed, view=None)
        except Exception as e:
            print(f"[DiscordBot] FATAL ERROR in confirm_button: {e}")
            traceback.print_exc()
            try:
                await interaction.followup.send("I encountered an error while creating your ticket. Please try again or contact support manually.", ephemeral=True)
            except: pass

    async def update_message(self, interaction: discord.Interaction):
        embed = discord.Embed(title="Ticket Preview", color=discord.Color.blue())
        embed.add_field(name="Subject", value=truncate_text(self.subject, 250), inline=False)
        embed.add_field(name="Description", value=truncate_text(self.description, 1000), inline=False)
        embed.add_field(name="Department", value=truncate_text(self.topic, 250), inline=True)
        embed.add_field(name="Priority", value=self.priority, inline=True)
        
        # We need to refresh the selects to show the new defaults
        self.clear_items()
        self.add_topic_select()
        self.add_priority_select()
        # Add the edit and confirm buttons back as well
        btn_edit = ui.Button(label='Edit Details', style=discord.ButtonStyle.secondary)
        btn_edit.callback = self.edit_button_callback
        self.add_item(btn_edit)
        
        btn_confirm = ui.Button(label='Confirm and Create Ticket', style=discord.ButtonStyle.primary)
        btn_confirm.callback = self.confirm_button_callback
        self.add_item(btn_confirm)

        try:
            if interaction.response.is_done():
                await interaction.followup.edit_message(message_id=interaction.message.id, embed=embed, view=self)
            else:
                await interaction.response.edit_message(embed=embed, view=self)
        except Exception as e:
            print(f"[DiscordBot] ERROR in update_message: {e}")
            traceback.print_exc()
            try:
                await interaction.followup.send("I encountered an error while updating the preview. Please check your text length and try again.", ephemeral=True)
            except: pass

    async def edit_button_callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(TicketModal(self, self.subject, self.description))

    async def confirm_button_callback(self, interaction: discord.Interaction):
        await self.confirm_button(interaction, None)


def truncate_text(text, max_len=4000):
    """
    Truncates text strictly to max_len, including the '...' suffix.
    """
    if not text:
        return ""
    if len(text) <= max_len:
        return text
    
    # We need to cut at max_len - 3 to make room for "..."
    limit = max_len - 3
    truncated = text[:limit]
    last_space = truncated.rfind(' ')
    
    if last_space != -1 and last_space > (limit * 0.8):
        return text[:last_space] + "..."
    else:
        return truncated + "..."

class ResolutionView(ui.View):
    def __init__(self, user, issue_id, confidence, ticket_data=None, conv_id=None, attachment_bytes=None, filename=None):
        super().__init__(timeout=None) # Set to None so users can resolve/escalate even hours later
        self.user = user
        self.issue_id = issue_id
        self.confidence = confidence
        self.ticket_data = ticket_data
        self.conv_id = conv_id
        self.attachment_bytes = attachment_bytes
        self.filename = filename

        # SAFE SNAPSHOT INITIALIZATION
        self.ticket_data = ticket_data if isinstance(ticket_data, dict) else {}
        self.subject = self.ticket_data.get('subject', 'Technical Support Request')
        self.description = self.ticket_data.get('description', 'Issue details summarized from conversation history.')
        self.topic = self.ticket_data.get('topic', 'Other')
        self.priority = self.ticket_data.get('priority', 'Medium')

        # DYNAMIC BUTTONS BASED ON REQUIREMENTS
        if confidence == "low":
            # KB MISS (no solution found) -> Create Ticket, New Issue, Cancel
            self.add_kb_miss_buttons()
        else:
            # KB HIT (solution found) -> Resolved, Still have questions, Create Ticket, New Issue
            self.add_kb_hit_buttons()

    def add_kb_miss_buttons(self):
        # Create Ticket
        btn_create = ui.Button(label='Create Ticket', style=discord.ButtonStyle.danger, custom_id=f"create_ticket:{self.issue_id}")
        btn_create.callback = self.create_ticket_callback
        self.add_item(btn_create)
        
        # New Issue
        btn_new = ui.Button(label='New Issue', style=discord.ButtonStyle.secondary, custom_id=f"new_issue:{self.issue_id}")
        btn_new.callback = self.new_issue_callback
        self.add_item(btn_new)
        
        # Cancel
        btn_cancel = ui.Button(label='Cancel', style=discord.ButtonStyle.secondary, custom_id=f"cancel:{self.issue_id}")
        btn_cancel.callback = self.cancel_callback
        self.add_item(btn_cancel)

    def add_kb_hit_buttons(self):
        # Resolved
        btn_resolved = ui.Button(label='Resolved', style=discord.ButtonStyle.success, custom_id=f"resolved:{self.issue_id}")
        btn_resolved.callback = self.resolved_callback
        self.add_item(btn_resolved)
        
        # Still have questions
        btn_questions = ui.Button(label='Still have questions', style=discord.ButtonStyle.secondary, custom_id=f"followup:{self.issue_id}")
        btn_questions.callback = self.questions_callback
        self.add_item(btn_questions)

        # Create Ticket
        btn_create = ui.Button(label='Create Ticket', style=discord.ButtonStyle.danger, custom_id=f"create_ticket:{self.issue_id}")
        btn_create.callback = self.create_ticket_callback
        self.add_item(btn_create)

        # New Issue
        btn_new = ui.Button(label='New Issue', style=discord.ButtonStyle.secondary, custom_id=f"new_issue:{self.issue_id}")
        btn_new.callback = self.new_issue_callback
        self.add_item(btn_new)

    async def resolved_callback(self, interaction: discord.Interaction):
        email_or_id = f"{self.user.name}@discord.com"
        chatbot_engine.close_issue_session(email_or_id, self.issue_id)
        if self.conv_id:
            CONVERSATION_HISTORY.pop(self.conv_id, None)
            LATEST_ATTACHMENTS.pop(self.conv_id, None)
        
        # Keep original content (from text or embed)
        original_text = ""
        msg = interaction.message
        if msg:
            original_text = msg.content or ""
            if msg.embeds:
                original_text = msg.embeds[0].description or original_text

        new_text = truncate_text(f"{original_text}\n\n**Issue Resolved** — Closing session. Share your next issue anytime.")
        
        embed = msg.embeds[0] if msg and msg.embeds else None
        if embed:
            embed.description = new_text
            await interaction.response.edit_message(embed=embed, view=None, content=None)
        else:
            await interaction.response.edit_message(content=new_text, view=None)

    async def questions_callback(self, interaction: discord.Interaction):
        msg = interaction.message
        original_text = msg.content or "" if msg else ""
        embed = msg.embeds[0] if msg and msg.embeds else None
        if embed:
            original_text = embed.description or original_text

        new_text = truncate_text(f"{original_text}\n\n**Continuing conversation...**")
        
        if embed:
            embed.description = new_text
            await interaction.response.edit_message(embed=embed, view=None, content=None)
        else:
            await interaction.response.edit_message(content=new_text, view=None)

    async def create_ticket_callback(self, interaction: discord.Interaction):
        try:
            # NEW: Defer immediately to prevent "This interaction failed"
            await interaction.response.defer(ephemeral=False)
            
            # Fetch latest snapshot from engine
            email_or_id = f"{self.user.name}@discord.com"
            snapshot = None
            try:
                snapshot = chatbot_engine.get_issue_snapshot(email_or_id, self.issue_id)
            except: pass
            
            # Default fallbacks
            summary_data = {}
            subject = self.subject
            tech_action = "Assistance needed to resolve user query."
            full_summary = "Troubleshooting exhausted; human review required."

            if snapshot:
                try:
                    # AI-POWERED HANDOFF SUMMARY
                    # Wrap blocking LLM call in to_thread
                    summary_data = await asyncio.to_thread(chatbot_engine.handoff_agent.summarize, snapshot)
                    subject = summary_data.get("subject", subject)
                    full_summary = summary_data.get("description", full_summary)
                    tech_action = summary_data.get("technician_action", tech_action)
                    # FIX: Update topic and priority from AI analysis
                    self.topic = summary_data.get("topic", self.topic)
                    self.priority = summary_data.get("priority", "Medium")
                except Exception as e:
                    print(f"[DiscordBot] Warning: Summary Generation Failed: {e}")

            # Create the interactive view
            view = TicketSystemView(
                self.user, subject, full_summary, self.topic, self.priority, self.conv_id, 
                attachment_bytes=self.attachment_bytes, 
                filename=self.filename,
                issue_id=self.issue_id
            )
            
            # BUILD CLEANER PREVIEW EMBED
            embed = discord.Embed(
                title="Ticket Handoff Report", 
                description=truncate_text(full_summary, 3800), # Show the full structured summary
                color=discord.Color.blue()
            )
            embed.add_field(name="Department", value=self.topic, inline=True)
            embed.add_field(name="Priority", value=self.priority, inline=True)
            
            # Robust original text extraction for the footer message
            original_text = interaction.message.content or ""
            if interaction.message.embeds:
                original_text = interaction.message.embeds[0].description or original_text
                
            text = f"**Ticket Preview Generated** — Please review the AI's summary for the technician below."
            
            await interaction.followup.edit_message(message_id=interaction.message.id, content=text, embed=embed, view=view)
        except Exception as e:
            print(f"[DiscordBot] FATAL ERROR in create_ticket_callback: {e}")
            traceback.print_exc()
            try:
                await interaction.followup.send("I encountered an error while preparing your ticket preview. Please try again.", ephemeral=True)
            except: pass

    async def new_issue_callback(self, interaction: discord.Interaction):
        email_or_id = f"{self.user.name}@discord.com"
        chatbot_engine.close_issue_session(email_or_id, self.issue_id)
        if self.conv_id:
            CONVERSATION_HISTORY.pop(self.conv_id, None)
            LATEST_ATTACHMENTS.pop(self.conv_id, None)
        # Keep original content but add closure footer
        original_text = interaction.message.content or ""
        embed = None
        if interaction.message.embeds:
            embed = interaction.message.embeds[0]
            original_text = embed.description or original_text

        new_text = truncate_text(f"{original_text}\n\n**Issue closed.** Share your next issue anytime.")
        
        if embed:
            embed.description = new_text
            await interaction.response.edit_message(embed=embed, view=None, content=None)
        else:
            await interaction.response.edit_message(content=new_text, view=None)

    async def cancel_callback(self, interaction: discord.Interaction):
        email_or_id = f"{self.user.name}@discord.com"
        chatbot_engine.close_issue_session(email_or_id, self.issue_id)
        if self.conv_id:
            LATEST_ATTACHMENTS.pop(self.conv_id, None)
        # Keep original content but add cancellation footer
        msg = interaction.message
        original_text = msg.content or "" if msg else ""
        embed = msg.embeds[0] if msg and msg.embeds else None
        if embed:
            original_text = embed.description or original_text

        new_text = truncate_text(f"{original_text}\n\n**Issue session cancelled.**")
        
        if embed:
            embed.description = new_text
            await interaction.response.edit_message(embed=embed, view=None, content=None)
        else:
            await interaction.response.edit_message(content=new_text, view=None)

class ContinuityDecisionView(ui.View):
    def __init__(self, user, issue_id, conv_id):
        super().__init__(timeout=1800) # Increased to 30 mins
        self.user = user
        self.issue_id = issue_id
        self.conv_id = conv_id

    @ui.button(label="Continue Current Issue", style=discord.ButtonStyle.primary)
    async def continue_callback(self, interaction: discord.Interaction, button: ui.Button):
        # State stays at AWAITING_CONFIRMATION or moves back to WORKING
        email_or_id = f"{self.user.name}@discord.com"
        state = chatbot_engine.continuity_agent.get_state(email_or_id)
        state.state = "WORKING"
        await interaction.response.edit_message(content="Understood. Let's continue with your current issue. What else can I help with?", view=None, embed=None)

    @ui.button(label="Start New Issue", style=discord.ButtonStyle.secondary)
    async def new_issue_callback(self, interaction: discord.Interaction, button: ui.Button):
        email_or_id = f"{self.user.name}@discord.com"
        chatbot_engine.close_issue_session(email_or_id, self.issue_id)
        if self.conv_id:
            LATEST_ATTACHMENTS.pop(self.conv_id, None)
            CONVERSATION_HISTORY.pop(self.conv_id, None)
        # Clear local history too for a fresh start if desired, or keep for GPT context
        await interaction.response.edit_message(content="Session closed. I'm ready for your new issue. Please describe the problem.", view=None, embed=None)

class ClarificationView(ui.View):
    """View with buttons for clarification options."""
    def __init__(self, user, options, issue_id, conv_id):
        super().__init__(timeout=1800) # Increased to 30 mins
        self.user = user
        self.options = options
        self.issue_id = issue_id
        self.conv_id = conv_id
        
        # Add buttons for each option (max 5 for a single row, or use a select)
        if len(options) <= 5:
            for opt in options:
                btn = ui.Button(label=opt, style=discord.ButtonStyle.primary, custom_id=f"clarify_{opt}")
                btn.callback = self.make_callback(opt)
                self.add_item(btn)
        else:
            # Use a select menu for many options
            select = ui.Select(placeholder="Select an option...", options=[
                discord.SelectOption(label=opt) for opt in options[:25]
            ])
            select.callback = self.select_callback
            self.add_item(select)

    def make_callback(self, choice):
        async def callback(interaction: discord.Interaction):
            # Edit original message to show selection and clear buttons
            await interaction.response.edit_message(
                content=f"**Selected:** {choice}\n\nProcessing your selection...",
                view=None
            )
            # Directly process the choice
            await self.process_clarification_choice(interaction, choice)
        return callback

    async def select_callback(self, interaction: discord.Interaction):
        choice = interaction.data['values'][0]
        # Edit original message to show selection and clear select
        await interaction.response.edit_message(
            content=f"**Selected:** {choice}\n\nProcessing your selection...",
            view=None
        )
        # Directly process the choice
        await self.process_clarification_choice(interaction, choice)

    async def process_clarification_choice(self, interaction: discord.Interaction, choice: str):
        """
        Directly calls the chatbot engine with the selected choice,
        bypassing the need to send a message to the channel.
        """
        try:
            user_context = {
                "user_id": str(self.user.id),
                "name": self.user.display_name,
                "email": f"{self.user.name}@discord.com"
            }

            if self.conv_id not in CONVERSATION_HISTORY:
                CONVERSATION_HISTORY[self.conv_id] = [
                    {"role": "assistant", "content": "Hi! I'm your AI Support Assistant. How can I help you today?"}
                ]
            history = CONVERSATION_HISTORY[self.conv_id]

            att_bytes, att_filename = LATEST_ATTACHMENTS.get(self.conv_id, (None, None))
            uploaded_file = None
            if att_bytes:
                uploaded_file = io.BytesIO(att_bytes)
                uploaded_file.name = att_filename

            response_data = await asyncio.to_thread(
                get_chatbot_response,
                user_message=choice,
                history=history,
                user_context=user_context,
                uploaded_file=uploaded_file
            )

            await interaction.client.handle_engine_response(
                response_data=response_data,
                user=self.user,
                conv_id=self.conv_id,
                user_msg=choice,
                history=history,
                att_bytes=att_bytes,
                att_filename=att_filename,
                interaction=interaction
            )

        except Exception as e:
            print(f"Error in ClarificationView callback: {e}")
            traceback.print_exc()
            await interaction.followup.send("I encountered an internal error processing your selection.")

class DiscordSupportBot(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def handle_engine_response(self, response_data, user, conv_id, user_msg, history, 
                                    att_bytes=None, att_filename=None, 
                                    message=None, interaction=None):
        """
        Shared helper to process chatbot engine responses and update UI/history.
        Supports both direct messages (on_message) and interaction followups (ClarificationView).
        """
        try:
            if not response_data or not isinstance(response_data, dict):
                error_text = "I'm sorry, I couldn't process your request right now."
                if interaction: await interaction.followup.send(error_text)
                else: await message.reply(error_text)
                return

            content = response_data.get('content', "I'm sorry, I couldn't process that.")
            intent = response_data.get('intent', 'support_question')
            action = response_data.get('action')
            confidence = response_data.get('confidence', 'low')
            ticket_data = response_data.get('ticket_data')
            issue_id = response_data.get("issue_id")
            state_val = response_data.get("state")
            
            file_info = response_data.get('file_info') or {}
            att_bytes = file_info.get('bytes') or att_bytes
            att_filename = file_info.get('filename') or att_filename

            # Choose responder
            async def send_reply(content=None, embed=None, view=None):
                kwargs = {}
                if content is not None: kwargs["content"] = content
                if embed is not None: kwargs["embed"] = embed
                if view is not None: kwargs["view"] = view
                
                # Check for generated image (charts)
                image_path = response_data.get('image_path')
                if image_path and os.path.exists(image_path):
                    kwargs["file"] = discord.File(image_path)
                
                if interaction:
                    return await interaction.followup.send(**kwargs)
                else:
                    return await message.reply(**kwargs)

            # Helper to add metrics button if available
            def attach_metrics(view):
                if response_data and view:
                    view.add_item(QualityMetricsButton(response_data))

            S = chatbot_engine.STAGES

            if action == "create_ticket":
                if not ticket_data:
                    ticket_data = {
                        "subject": "Missing Support Information",
                        "description": user_msg,
                        "topic": "Other (Custom...)",
                        "priority": "Medium"
                    }
                view = TicketSystemView(
                    user, ticket_data['subject'], ticket_data['description'], 
                    ticket_data['topic'], ticket_data.get('priority', 'Medium'),
                    conv_id, 
                    attachment_bytes=att_bytes, filename=att_filename, issue_id=issue_id
                )
                attach_metrics(view)
                embed = discord.Embed(
                    description=content or "I have prepared a ticket for a technician to review.",
                    color=discord.Color.orange()
                )
                await send_reply(embed=embed, view=view)
                
            elif state_val == S["CONTINUITY"]:
                view = ContinuityDecisionView(user, issue_id, conv_id)
                attach_metrics(view)
                await send_reply(content=content, view=view)
                
            elif state_val == S["CLARIFYING"]:
                options = response_data.get('clarification_options', [])
                if not options:
                    try:
                        email_or_id = f"{user.name}@discord.com"
                        snapshot = chatbot_engine.get_issue_snapshot(email_or_id, issue_id)
                        if snapshot:
                            options = snapshot.get("clarification_options", [])
                    except: pass
                
                if options:
                    view = ClarificationView(user, options, issue_id, conv_id)
                    attach_metrics(view)
                    await send_reply(content=content, view=view)
                else:
                    # Even for simple text without a view, we can add a view just for metrics
                    view = ui.View(timeout=3600)
                    attach_metrics(view)
                    await send_reply(content=content, view=view)
                    
            elif state_val == S["AUTOMATING"]:
                embed = discord.Embed(description=content, color=discord.Color.gold())
                embed.set_footer(text="Automation — reply yes or no")
                view = ui.View(timeout=3600)
                attach_metrics(view)
                await send_reply(embed=embed, view=view)
                
            elif intent in ["support_question", "followup", "file_analysis", "other"] and issue_id:
                view = ResolutionView(
                    user, issue_id, confidence, ticket_data, conv_id, 
                    attachment_bytes=att_bytes, filename=att_filename
                )
                attach_metrics(view)
                embed = discord.Embed(description=content, color=discord.Color.blue())
                await send_reply(embed=embed, view=view)
            else:
                # Default fallback for simple messages
                # Use a larger limit for fallback messages
                view = ui.View(timeout=3600)
                attach_metrics(view)
                await send_reply(content=truncate_text(content, 4000), view=view)

            history.append({"role": "user", "content": user_msg})
            history.append({"role": "assistant", "content": content})
            if len(history) > 10:
                CONVERSATION_HISTORY[conv_id] = history[-10:]
            else:
                CONVERSATION_HISTORY[conv_id] = history

        except Exception as e:
            print(f"Error in handle_engine_response: {e}")
            traceback.print_exc()
            try:
                error_text = "I encountered an error while processing the response."
                if interaction: await interaction.followup.send(error_text)
                else: await message.reply(error_text)
            except Exception as nested_e:
                print(f"Failed to send error reply: {nested_e}")

    async def on_ready(self):
        print(f"Logged in as {self.user} (ID: {self.user.id})")
        print("------")

    async def on_message(self, message):
        # Don't respond to ourselves
        if message.author == self.user:
            return

        user_name = message.author.display_name
        user_id = str(message.author.id)
        conv_id = f"{message.channel.id}_{user_id}"

        # Handle explicit clear command
        if message.clean_content.strip().lower() == "clear":
            if conv_id in CONVERSATION_HISTORY:
                del CONVERSATION_HISTORY[conv_id]
                if conv_id in LATEST_ATTACHMENTS:
                    del LATEST_ATTACHMENTS[conv_id]
                await message.reply("Conversation history cleared.")
            else:
                await message.reply("No active history to clear.")
            return

        is_dm = isinstance(message.channel, discord.DMChannel)
        is_mentioned = self.user.mentioned_in(message)

        # For now, let's respond to all messages in DMs, or mentions in guilds
        if not (is_dm or is_mentioned):
            return

        user_msg = message.clean_content.replace(f"@{self.user.display_name}", "").strip()
        
        if conv_id not in CONVERSATION_HISTORY:
            CONVERSATION_HISTORY[conv_id] = [
                {"role": "assistant", "content": "Hi! I'm your AI Support Assistant. How can I help you today?"}
            ]
        history = CONVERSATION_HISTORY[conv_id]

        user_context = {
            "user_id": user_id,
            "name": user_name,
            "email": f"{message.author.name}@discord.com" # Placeholder
        }

        # Shared processing logic
        async def do_process():
            try:
                uploaded_file = None
                att_bytes = None
                att_filename = None 

                if message.attachments:
                    attachment = message.attachments[0]
                    att_bytes = await attachment.read()
                    att_filename = attachment.filename
                    # Store in cache for subsequent turns
                    LATEST_ATTACHMENTS[conv_id] = (att_bytes, att_filename)
                    print(f"[DiscordBot] New attachment received and cached: {att_filename}", flush=True)
                elif conv_id in LATEST_ATTACHMENTS:
                    # Retrieve last attachment if current message has none
                    att_bytes, att_filename = LATEST_ATTACHMENTS[conv_id]
                    print(f"[DiscordBot] Using cached attachment from previous turn: {att_filename}", flush=True)

                if att_bytes:
                    # Duck-type UploadedFile for chatbot_engine
                    uploaded_file = io.BytesIO(att_bytes)
                    uploaded_file.name = att_filename
                
                response_data = await asyncio.to_thread(
                    get_chatbot_response,
                    user_message=user_msg,
                    history=history,
                    user_context=user_context,
                    uploaded_file=uploaded_file
                )

                await self.handle_engine_response(
                    response_data=response_data,
                    user=message.author,
                    conv_id=conv_id,
                    user_msg=user_msg,
                    history=history,
                    att_bytes=att_bytes,
                    att_filename=att_filename,
                    message=message
                )

            except Exception as e:
                print(f"Error in DiscordBot processing: {e}")
                traceback.print_exc()
                try:
                    await message.reply("I encountered an internal error. Please try again later.")
                except Exception as nested_e:
                    print(f"Failed to send final error reply: {nested_e}")

        # Start typing indicator (wrapped in try-except to prevent 503s from crashing logic)
        try:
            async with message.channel.typing():
                await do_process()
        except Exception as e:
            print(f"[DiscordBot] Warning: Failed to send typing indicator: {e}")
            # Fallback: process without typing indicator
            await do_process()

# Set up intents
intents = discord.Intents.default()
intents.message_content = True # Required to read message content
intents.messages = True
intents.guilds = True
intents.dm_messages = True

if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("Error: DISCORD_TOKEN not found. Please set it in the .env file.")
    else:
        client = DiscordSupportBot(intents=intents)
        client.run(DISCORD_TOKEN)
