#!/usr/bin/env python3
"""
Create realistic test data that will show meaningful correlations between categories.
This version creates more varied patterns so correlations aren't all 1.0.
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import Project, Result
import random
from datetime import datetime, timedelta

def create_realistic_test_data():
    """Create test data with realistic category patterns for meaningful correlations."""
    
    # Clear existing data
    with app.app_context():
        # Delete existing results for this project
        project = Project.query.filter_by(slug='realistic-test-dataset').first()
        if project:
            Result.query.filter_by(project_id=project.id).delete()
            db.session.delete(project)
            db.session.commit()
        
        # Create project
        project = Project(
            slug='realistic-test-dataset',
            name='Realistic Test Dataset',
            created_at=datetime.now()
        )
        db.session.add(project)
        db.session.commit()
        
        # Define categories and tags with realistic patterns
        categories = {
            'Content Type': ['News/Current Events', 'Lifestyle', 'Entertainment', 'Educational', 'Product Review', 'Tutorial/How-to'],
            'Target Audience': ['Children', 'Teens (13-17)', 'Young Adults (18-25)', 'Adults (26+)', 'General Audience'],
            'Engagement Style': ['Behind-the-scenes', 'Storytelling', 'Direct Address', 'Demonstration', 'Reaction', 'Interactive'],
            'Visual Style': ['Text Overlay', 'Screen Recording', 'Wide Shot', 'Close-up', 'Split Screen', 'Animation'],
            'Tone': ['Casual', 'Informative', 'Humorous', 'Serious', 'Inspirational', 'Dramatic']
        }
        
        # Define realistic patterns (some categories appear together more often)
        patterns = {
            # News content tends to be informative and use text overlay
            'news_pattern': {
                'Content Type': ['News/Current Events'],
                'Tone': ['Informative', 'Serious'],
                'Visual Style': ['Text Overlay'],
                'probability': 0.3
            },
            # Educational content tends to be tutorial-style with demonstrations
            'educational_pattern': {
                'Content Type': ['Educational', 'Tutorial/How-to'],
                'Engagement Style': ['Demonstration'],
                'Tone': ['Informative'],
                'probability': 0.25
            },
            # Entertainment content tends to be humorous and casual
            'entertainment_pattern': {
                'Content Type': ['Entertainment'],
                'Tone': ['Humorous', 'Casual'],
                'Engagement Style': ['Reaction'],
                'probability': 0.2
            },
            # Lifestyle content tends to be inspirational with storytelling
            'lifestyle_pattern': {
                'Content Type': ['Lifestyle'],
                'Tone': ['Inspirational'],
                'Engagement Style': ['Storytelling'],
                'probability': 0.15
            },
            # Product reviews tend to be demonstrations with close-ups
            'review_pattern': {
                'Content Type': ['Product Review'],
                'Engagement Style': ['Demonstration'],
                'Visual Style': ['Close-up'],
                'probability': 0.1
            }
        }
        
        coders = ['Alice Johnson', 'Bob Smith', 'Carol Davis', 'David Wilson']
        statuses = ['submitted', 'saved', 'excluded']
        status_weights = [0.85, 0.10, 0.05]  # 85% submitted, 10% saved, 5% excluded
        
        # Generate 80 videos with realistic patterns
        for video_num in range(1, 81):
            video_id = f"video_{video_num:03d}"
            
            for coder in coders:
                # Determine status
                status = random.choices(statuses, weights=status_weights)[0]
                
                if status == 'excluded':
                    # Excluded videos have no categories
                    categories_str = ""
                    notes = ""
                else:
                    # Apply realistic patterns
                    selected_categories = {}
                    
                    # Choose a pattern to follow
                    pattern_choice = random.random()
                    cumulative_prob = 0
                    applied_pattern = None
                    
                    for pattern_name, pattern_data in patterns.items():
                        cumulative_prob += pattern_data['probability']
                        if pattern_choice <= cumulative_prob:
                            applied_pattern = pattern_data
                            break
                    
                    # Apply pattern categories
                    if applied_pattern:
                        for category, tags in applied_pattern.items():
                            if category != 'probability':
                                selected_categories[category] = random.sample(tags, min(len(tags), random.randint(1, 2)))
                    
                    # Fill in remaining categories randomly (but not always)
                    for category, all_tags in categories.items():
                        if category not in selected_categories:
                            # 70% chance to include each remaining category
                            if random.random() < 0.7:
                                num_tags = random.randint(1, min(3, len(all_tags)))
                                selected_categories[category] = random.sample(all_tags, num_tags)
                    
                    # Build categories string
                    category_parts = []
                    for category, tags in selected_categories.items():
                        category_parts.append(f"{category}: {', '.join(tags)}")
                    categories_str = "; ".join(category_parts)
                    
                    # Generate notes
                    note_templates = [
                        "Interesting content, well-produced.",
                        "Good engagement with audience.",
                        "Relatable content for target audience.",
                        "Creative approach to the topic.",
                        "Effective use of visual elements.",
                        "Engaging storytelling approach.",
                        ""
                    ]
                    notes = random.choice(note_templates)
                
                # Generate timestamp
                base_time = datetime.now() - timedelta(days=random.randint(1, 30))
                timestamp = base_time + timedelta(hours=random.randint(0, 23), minutes=random.randint(0, 59))
                
                # Create result
                result = Result(
                    project_id=project.id,
                    coder_id=1,  # We'll use a default coder ID
                    video_id=video_id,
                    status=status,
                    timestamp=timestamp,
                    notes=notes,
                    categories=categories_str
                )
                db.session.add(result)
        
        db.session.commit()
        print(f"Created realistic test data with {80 * 4} results (80 videos × 4 coders)")
        print("This dataset should show meaningful correlations between categories!")

if __name__ == '__main__':
    create_realistic_test_data()
