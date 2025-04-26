# TaskIndexManager.py
from collections import defaultdict

# Global variable to store the task index
TasksIndex = defaultdict(list)

def update_index_after_delete(task_id, task_title=None):
    """Update TasksIndex after a task is deleted."""
    try:
        print(f"Updating index for task {task_id}")
        
        # Remove the task ID from all index entries
        for term, task_ids in list(TasksIndex.items()):
            if task_id in task_ids:
                TasksIndex[term].remove(task_id)
                # Clean up empty entries
                if not TasksIndex[term]:
                    del TasksIndex[term]
        
        print("Index updated successfully")
        return True
    except Exception as e:
        print(f"Error updating index: {e}")
        return False

def add_to_index(task_id, task_title, task_description=None):
    """Add a task to the search index."""
    try:
        # Process title
        if task_title:
            words = task_title.lower().split()
            for word in words:
                # Remove any punctuation
                word = word.strip('.,!?;:()[]{}"\'-')
                if word and len(word) > 2:  # Only index words longer than 2 characters
                    TasksIndex[word].append(task_id)
        
        # Process description
        if task_description:
            words = task_description.lower().split()
            for word in words:
                # Remove any punctuation
                word = word.strip('.,!?;:()[]{}"\'-')
                if word and len(word) > 2:  # Only index words longer than 2 characters
                    TasksIndex[word].append(task_id)
        
        print(f"Task {task_id} added to index successfully")
        return True
    except Exception as e:
        print(f"Error adding to index: {e}")
        return False

def search_index(search_terms):
    """Search the index for tasks matching the given terms."""
    try:
        if not isinstance(search_terms, list):
            search_terms = [search_terms]
        
        # Process search terms
        search_results = set()
        for term in search_terms:
            term = term.lower().strip()
            if term in TasksIndex:
                # Add all task IDs that match this term
                search_results.update(TasksIndex[term])
        
        return list(search_results)
    except Exception as e:
        print(f"Error searching index: {e}")
        return []

