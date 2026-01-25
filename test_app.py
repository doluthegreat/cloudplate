import pytest
from app import app, db, Restaurant, Review

@pytest.fixture
def client():
    """Create a test client"""
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:200603@localhost:5432/restaurant_test_db'
    
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client
        with app.app_context():
            db.drop_all()

def test_home(client):
    """Test home endpoint returns welcome message"""
    response = client.get('/')
    assert response.status_code == 200
    data = response.get_json()
    assert "message" in data

def test_create_restaurant(client):
    """Test creating a new restaurant"""
    response = client.post('/restaurants',
                          json={'name': 'Test Restaurant', 'location': 'Test Location'})
    assert response.status_code == 201
    data = response.get_json()
    assert data['name'] == "Test Restaurant"
    assert data['location'] == "Test Location"

def test_get_restaurants(client):
    """Test getting all restaurants"""
    client.post('/restaurants', json={'name': 'Test', 'location': 'Lagos'})
    
    response = client.get('/restaurants')
    assert response.status_code == 200
    data = response.get_json()
    assert "restaurants" in data

def test_update_restaurant(client):
    """Test updating a restaurant"""
    create_response = client.post('/restaurants',
                                  json={'name': 'Old Name', 'location': 'Old Location'})
    restaurant_id = create_response.get_json()['id']
    
    response = client.put(f'/restaurants/{restaurant_id}',
                         json={'name': 'New Name'})
    assert response.status_code == 200
    data = response.get_json()
    assert data['name'] == "New Name"

def test_delete_restaurant(client):
    """Test deleting a restaurant"""
    create_response = client.post('/restaurants',
                                  json={'name': 'Delete Me', 'location': 'Test'})
    restaurant_id = create_response.get_json()['id']
    
    response = client.delete(f'/restaurants/{restaurant_id}')
    assert response.status_code == 200
    
    get_response = client.get(f'/restaurants/{restaurant_id}')
    assert get_response.status_code == 404

def test_create_review(client):
    """Test creating a review with sentiment analysis"""
    restaurant_response = client.post('/restaurants',
                                     json={'name': 'Test', 'location': 'Lagos'})
    restaurant_id = restaurant_response.get_json()['id']
    
    response = client.post('/reviews',
                          json={'restaurant_id': restaurant_id, 
                                'text': 'Amazing food!'})
    assert response.status_code == 201
    data = response.get_json()
    assert data['sentiment_label'] == 'positive'
    assert data['sentiment_score'] > 0