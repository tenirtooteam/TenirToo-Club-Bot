import pytest
from database import db

def test_create_and_get_audit_request():
    user_id = 12345
    db.add_user(user_id, "Test", "User") # Ensure user exists for FK
    u_id = db.create_audit_request(user_id, "test_type", 10)
    assert u_id > 0
    
    req = db.get_audit_request(u_id)
    assert req is not None
    assert req["user_id"] == user_id
    assert req["entity_type"] == "test_type"
    assert req["status"] == "pending"

def test_resolve_audit_request():
    user_id = 999
    db.add_user(user_id, "Admin", "Test") # Ensure user exists
    u_id = db.create_audit_request(user_id, "event_approval", 50)
    
    # Approve
    success = db.resolve_audit_request(u_id, "approved", "Looks good")
    assert success is True
    
    req = db.get_audit_request(u_id)
    assert req["status"] == "approved"
    assert req["comment"] == "Looks good"

def test_get_pending_requests():
    db.add_user(1, "U1", "")
    db.add_user(2, "U2", "")
    db.add_user(3, "U3", "")
    db.create_audit_request(1, "type_a", 100)
    db.create_audit_request(2, "type_a", 100)
    db.create_audit_request(3, "type_b", 100)
    
    pending_a = db.get_pending_requests_by_type("type_a", 100)
    assert len(pending_a) == 2
    
    pending_b = db.get_pending_requests_by_type("type_b", 100)
    assert len(pending_b) == 1

def test_get_user_pending_request():
    user_id = 777
    db.add_user(user_id, "U777", "")
    db.create_audit_request(user_id, "participation", 5)
    
    req_id = db.get_user_pending_request(user_id, "participation", 5)
    assert req_id is not None
    
    # After resolving, it shouldn't find it as 'pending'
    db.resolve_audit_request(req_id, "approved")
    assert db.get_user_pending_request(user_id, "participation", 5) is None
