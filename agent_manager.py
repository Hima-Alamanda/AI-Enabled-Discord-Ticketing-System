import database
import uuid
import random
import utils

# Define the list of generated agents

# Topics: "Finance", "HR", "Supply Chain", "Manufacturing", "Sales", "IT Infrastructure & Hardware", "Access & Identity", "Other"
# Instances: "DEV - Development", "QA / TEST - Testing", "UAT - User Acceptance Testing", "PROD - Production"

def init_agents():
    """
    Initializes the database with 16 fake agents + 2 real users if they don't exist.
    """
    existing_agents = database.get_all_agents()
    # Ideally 18 agents (2 real + 16 fake) 
    if len(existing_agents) >= 18:
        return # Already initialized

    print("Initializing Agents...")
    
    existing_emails = {a['email'] for a in existing_agents}
    
    real_agents = [
        {
            "name": "Himanth",
            "email": "himanth@pcbapps.com",
            "role": "admin",
            # Give real agents broad access
            "topics": utils.TICKET_TOPICS, 
            "instances": utils.INSTANCES 
        },
        {
            "name": "Admin",
            "email": "admin@pcbapps.com",
            "role": "admin",
            "topics": utils.TICKET_TOPICS,
            "instances": utils.INSTANCES
        }
    ]
    
    agents_to_create = []
    
    # Add real agents only if they don't exist
    for ra in real_agents:
        if ra['email'] not in existing_emails:
            agents_to_create.append(ra)
    
    # Strategy: 2 agents per topic, covering mixed instances
    fake_agents_data = []
    
    # Pre-define some skills to ensure coverage
    # 8 Topics. We create 2 agents for each topic as "Primary" experts.
    # They can cover all instances for simplicity, or we split instances.
    # Let's make them cover ALL instances for their specific topics to ensure availability.
    
    agent_names = [
        "Raghu", "Revanth", "Chinni", "Harshith",
        "Rohan", "Kaushik", "Vaishno", "Anil",
        "Karthik", "Sharanya", "Siva", "Bhanu",
        "Kasi", "Prathyusha", "Ganesh", "Aditya"
    ]
    
    # Distribution: 16 agents, 8 topics. Exactly 2 agents per topic.
    # Each agent covers ALL instances for their topic.
    
    topics = utils.TICKET_TOPICS # length 8
    
    full_instances = utils.INSTANCES
    
    for i, name in enumerate(agent_names):
        # Assign primary topic based on index
        # 0,1 -> Topic 0
        # 2,3 -> Topic 1
        topic_idx = i // 2
        if topic_idx < len(topics):
            primary_topic = topics[topic_idx]
            
            # Create agent
            agent = {
                "name": name,
                "email": f"{name.lower().replace(' ', '.')}@pcbapps.com",
                "topics": [primary_topic], # List
                "instances": full_instances # All instances
            }
            if agent['email'] not in existing_emails:
                agents_to_create.append(agent)
            
    # Save all to DB
    for agent_info in agents_to_create:
        # Generate Readable ID
        # e.g. "John Smith" -> "agent-john-smith"
        slug = agent_info['name'].lower().replace(" ", "-")
        agent_id = f"agent-{slug}"
        
        data = {
            "agent_id": agent_id,
            "name": agent_info['name'],
            "email": agent_info['email'],
            "role": agent_info.get('role', 'agent'),
            "topics": agent_info['topics'],
            "instances": agent_info['instances'],
            "active": 1
        }
        database.save_agent(data)
        print(f"Created agent: {agent_info['name']}")

def assign_agent(ticket_data):
    """
    Inteligently assigns an agent to the ticket.
    Logic:
    1. Filter agents who match the Ticket Topic AND Ticket Instance.
    2. Sort by Workload (number of active tickets).
    3. Return the ID of the best match.
    """
    ticket_topic = ticket_data.get('topic')
    ticket_instance = ticket_data.get('instance')
    
    if not ticket_topic:
        # If no topic, we can't do much, but maybe 'Other'?
        ticket_topic = "Other"

    all_agents = database.get_all_agents()
    
    all_agents = [a for a in all_agents if a.get('role') != 'admin']

    candidates = []
    for agent in all_agents:
        # Check Topic Match
        topic_match = ticket_topic in agent.get('topics', [])
        
        # Check Instance Match (Only if instance is provided)
        instance_match = True
        if ticket_instance:
             instance_match = ticket_instance in agent.get('instances', [])
        else:
             # Logic Change: If instance is missing, it's likely a Live Chat ticket.
             # Check if agent is enabled for Live Chat.
             # Default to True (1) if field missing/None
             if not agent.get('live_chat_active', 1):
                 instance_match = False
        
        if topic_match and instance_match:
            candidates.append(agent)
            
    # Fallback: If no one matches both, match Topic only
    if not candidates:
        for agent in all_agents:
            if ticket_topic in agent.get('topics', []):
                candidates.append(agent)
                
    # Fallback Level 2: If still no one, match 'Other' or anyone
    if not candidates:
        candidates = all_agents

    if not candidates:
        return None # No agents at all?
        
    workloads = database.get_agent_workload() # agent_id -> count
    
    # Sort candidates by workload (asc)
    # If agent not in workloads, count is 0
    candidates.sort(key=lambda x: workloads.get(x['agent_id'], 0))
    
    best_agent = candidates[0]
    
    print(f"Assigning ticket {ticket_data.get('ticket_id')} to {best_agent['name']} (Workload: {workloads.get(best_agent['agent_id'], 0)})")
    
    return best_agent['agent_id']
