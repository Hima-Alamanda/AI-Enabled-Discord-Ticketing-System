import matplotlib
matplotlib.use('Agg') # Force non-interactive backend for background chart generation
import matplotlib.pyplot as plt
import seaborn as sns
import os
import datetime
import uuid

# Configuration for Dark Theme Premium Look
plt.style.use('dark_background')
sns.set_palette("viridis") # Sleek colors (purple, blue, green)

CHART_DIR = "static/charts"

if not os.path.exists(CHART_DIR):
    os.makedirs(CHART_DIR)

def _get_save_path():
    """Generates a unique path for the new chart."""
    filename = f"chart_{uuid.uuid4().hex[:8]}.png"
    return os.path.join(CHART_DIR, filename)

def finalize_plot(plt, title):
    """Adds labels and saves the plot to a PNG file."""
    plt.title(title, fontsize=14, fontweight='bold', pad=20, color='#00d1ff')
    plt.tight_layout()
    path = _get_save_path()
    plt.savefig(path, dpi=150, facecolor='#121212') # Deep dark background
    plt.close()
    return os.path.abspath(path)

def create_bar_chart(labels, values, title="Support Metrics"):
    """Creates a sleek bar chart."""
    plt.figure(figsize=(10, 6))
    ax = sns.barplot(x=labels, y=values, palette="rocket")
    
    # Customizing axes
    plt.xticks(rotation=45, ha='right', color='white')
    plt.yticks(color='white')
    plt.ylabel("Count", color='white')
    
    # Add data labels on top of bars
    for p in ax.patches:
        ax.annotate(format(p.get_height(), '.1f'), 
                   (p.get_x() + p.get_width() / 2., p.get_height()), 
                   ha = 'center', va = 'center', 
                   xytext = (0, 9), 
                   textcoords = 'offset points',
                   color='white')

    return finalize_plot(plt, title)

def create_pie_chart(labels, values, title="Distribution"):
    """Creates a high-quality pie chart."""
    plt.figure(figsize=(8, 8))
    # Use sleek colors for the pie pieces
    colors = sns.color_palette("pastel")
    
    plt.pie(values, labels=labels, autopct='%1.1f%%', 
            startangle=140, colors=colors, 
            textprops={'color':"w", 'weight':'bold'})
    
    # Draw a circle at the center to make it a donut chart (it looks more premium)
    centre_circle = plt.Circle((0,0),0.70,fc='#121212') # Dark background
    fig = plt.gcf()
    fig.gca().add_artist(centre_circle)
    
    plt.axis('equal')
    return finalize_plot(plt, title)

def create_line_chart(dates, values, title="Activity Trends"):
    """Creates a sleek line chart."""
    plt.figure(figsize=(12, 6))
    sns.lineplot(x=dates, y=values, marker='o', linewidth=3, color='#00ffcc')
    
    plt.fill_between(dates, values, alpha=0.3, color='#00ffcc')
    
    plt.xticks(rotation=45, color='white')
    plt.yticks(color='white')
    
    return finalize_plot(plt, title)
