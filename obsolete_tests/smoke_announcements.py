# Файл: tests/smoke_announcements.py
import sys
import os
sys.path.append(os.getcwd())

from database import db

def test_announcements_db():
    print("Testing Announcements DB...")
    db.init_db()
    
    # Create
    ann_id = db.create_announcement(
        a_type="event", 
        target_id=1, 
        topic_id=123, 
        creator_id=999, 
        chat_id=-1001, 
        message_id=555
    )
    print(f"Created announcement with ID: {ann_id}")
    
    # Get
    ann = db.get_announcement(ann_id)
    print(f"Retrieved: {ann}")
    assert ann is not None
    assert ann[1] == "event"
    assert ann[3] == 123
    
    # Delete
    db.delete_announcements_by_target("event", 1)
    ann_after = db.get_announcement(ann_id)
    print(f"After deletion: {ann_after}")
    assert ann_after is None
    
    print("✅ Announcements DB test passed!")

if __name__ == "__main__":
    test_announcements_db()
