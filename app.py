from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import redis
import os

app = Flask(__name__)


DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:200603@postgres:5432/restaurant_db')
REDIS_HOST = os.getenv('REDIS_HOST', 'redis')

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


redis_client = redis.Redis(host=REDIS_HOST, port=6379, decode_responses=True)

analyzer = SentimentIntensityAnalyzer()

LEADERBOARD_KEY = 'restaurant:leaderboard'

class Restaurant(db.Model):
    __tablename__ = 'restaurants'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    reviews = db.relationship('Review', backref='restaurant', lazy=True, cascade='all, delete-orphan')
    
    def get_average_sentiment(self):
        """Calculate average sentiment score for this restaurant"""
        if not self.reviews:
            return 0
        total = sum(review.sentiment_score for review in self.reviews)
        return round(total / len(self.reviews), 2)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'location': self.location,
            'average_sentiment': self.get_average_sentiment(),
            'total_reviews': len(self.reviews),
            'created_at': self.created_at.isoformat()
        }

class Review(db.Model):
    __tablename__ = 'reviews'
    
    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    sentiment_score = db.Column(db.Float, nullable=False)
    sentiment_label = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'restaurant_id': self.restaurant_id,
            'text': self.text,
            'sentiment_score': self.sentiment_score,
            'sentiment_label': self.sentiment_label,
            'created_at': self.created_at.isoformat()
        }

def analyze_sentiment(text):
    """Analyze sentiment of text using VADER"""
    scores = analyzer.polarity_scores(text)
    compound_score = scores['compound']
    
    if compound_score >= 0.05:
        label = 'positive'
    elif compound_score <= -0.05:
        label = 'negative'
    else:
        label = 'neutral'
    
    return compound_score, label

def update_leaderboard(restaurant_id):
    """
    Update Redis leaderboard with restaurant's average sentiment
    Uses Redis SortedSet for O(log N) updates and queries
    """
    restaurant = Restaurant.query.get(restaurant_id)
    if restaurant and restaurant.reviews:
        avg_sentiment = restaurant.get_average_sentiment()
        redis_client.zadd(LEADERBOARD_KEY, {str(restaurant_id): avg_sentiment})
        print(f"Updated leaderboard: Restaurant {restaurant_id} -> {avg_sentiment}")

def get_leaderboard_from_redis():
    """
    Get top and bottom restaurants from Redis
    Returns restaurants sorted by sentiment (highest to lowest)
    """
    restaurant_ids = redis_client.zrevrange(LEADERBOARD_KEY, 0, -1, withscores=True)
    
    leaderboard = []
    for idx, (restaurant_id, score) in enumerate(restaurant_ids):
        restaurant = Restaurant.query.get(int(restaurant_id))
        if restaurant:
            leaderboard.append({
                'rank': idx + 1,
                'restaurant': restaurant.to_dict(),
                'cached_sentiment': round(score, 2)
            })
    
    return leaderboard

with app.app_context():
    db.create_all()

# Routes
@app.route('/')
def home():
    try:
        redis_client.ping()
        redis_status = "connected"
    except:
        redis_status = "disconnected"
    
    return jsonify({
        "message": "Restaurant Review API with Redis Leaderboard!",
        "redis_status": redis_status,
        "endpoints": {
            "GET /restaurants": "Get all restaurants",
            "POST /restaurants": "Add a new restaurant",
            "POST /reviews": "Add a review (updates leaderboard)",
            "GET /leaderboard": "Get Redis-powered leaderboard (FAST!)",
            "GET /leaderboard/top/<n>": "Get top N restaurants",
            "GET /leaderboard/bottom/<n>": "Get bottom N restaurants"
        }
    })

@app.route('/restaurants', methods=['GET'])
def get_restaurants():
    restaurants = Restaurant.query.all()
    return jsonify({
        "restaurants": [r.to_dict() for r in restaurants]
    })

@app.route('/restaurants', methods=['POST'])
def add_restaurant():
    data = request.get_json()
    
    if not data.get('name') or not data.get('location'):
        return jsonify({"error": "Name and location are required"}), 400
    
    restaurant = Restaurant(
        name=data['name'],
        location=data['location']
    )
    
    db.session.add(restaurant)
    db.session.commit()
    
    return jsonify(restaurant.to_dict()), 201

@app.route('/restaurants/<int:restaurant_id>', methods=['GET'])
def get_restaurant(restaurant_id):
    restaurant = Restaurant.query.get(restaurant_id)
    
    if not restaurant:
        return jsonify({"error": "Restaurant not found"}), 404
    
    return jsonify(restaurant.to_dict()) 

@app.route('/reviews', methods=['POST'])
def add_review():
    data = request.get_json()
    
    if not data.get('restaurant_id') or not data.get('text'):
        return jsonify({"error": "restaurant_id and text are required"}), 400
    
    restaurant = Restaurant.query.get(data['restaurant_id'])
    if not restaurant:
        return jsonify({"error": "Restaurant not found"}), 404
    
    sentiment_score, sentiment_label = analyze_sentiment(data['text'])
    
    review = Review(
        restaurant_id=data['restaurant_id'],
        text=data['text'],
        sentiment_score=sentiment_score,
        sentiment_label=sentiment_label
    )
    
    db.session.add(review)
    db.session.commit()
    
    update_leaderboard(data['restaurant_id'])
    
    return jsonify({
        **review.to_dict(),
        "leaderboard_updated": True
    }), 201

@app.route('/leaderboard', methods=['GET'])
def get_leaderboard():
    """Get full leaderboard from Redis"""
    leaderboard = get_leaderboard_from_redis()
    
    return jsonify({
        "leaderboard": leaderboard,
        "total_restaurants": len(leaderboard),
        "source": "Redis (cached)"
    })

@app.route('/leaderboard/top/<int:n>', methods=['GET'])
def get_top_restaurants(n):
    """Get top N restaurants by sentiment"""
    restaurant_ids = redis_client.zrevrange(LEADERBOARD_KEY, 0, n-1, withscores=True)
    
    top_restaurants = []
    for idx, (restaurant_id, score) in enumerate(restaurant_ids):
        restaurant = Restaurant.query.get(int(restaurant_id))
        if restaurant:
            top_restaurants.append({
                'rank': idx + 1,
                'restaurant': restaurant.to_dict(),
                'cached_sentiment': round(score, 2)
            })
    
    return jsonify({
        "top_restaurants": top_restaurants
    })

@app.route('/leaderboard/bottom/<int:n>', methods=['GET'])
def get_bottom_restaurants(n):
    """Get bottom N restaurants by sentiment"""

    restaurant_ids = redis_client.zrange(LEADERBOARD_KEY, 0, n-1, withscores=True)
    
    bottom_restaurants = []
    for idx, (restaurant_id, score) in enumerate(restaurant_ids):
        restaurant = Restaurant.query.get(int(restaurant_id))
        if restaurant:
            bottom_restaurants.append({
                'rank': idx + 1,
                'restaurant': restaurant.to_dict(),
                'cached_sentiment': round(score, 2)
            })
    
    return jsonify({
        "bottom_restaurants": bottom_restaurants
    })


@app.route('/restaurants/<int:restaurant_id>', methods=['DELETE'])
def delete_restaurant(restaurant_id):
    restaurant = Restaurant.query.get(restaurant_id)
    
    if not restaurant:
        return jsonify({"error": "Restaurant not found"}), 404
    
    db.session.delete(restaurant)
    db.session.commit()
    
    redis_client.zrem(LEADERBOARD_KEY, str(restaurant_id))
    
    return jsonify({"message": "Restaurant successfully deleted"}), 200
@app.route('/restaurants/<int:restaurant_id>', methods=['PUT'])
def update_restaurant(restaurant_id):
    data = request.get_json()
    
    restaurant = Restaurant.query.get(restaurant_id)
    
    if not restaurant:
        return jsonify({"error": "Restaurant not found"}), 404
    
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    if 'name' in data:
        restaurant.name = data['name']
    
    if 'location' in data:
        restaurant.location = data['location']
    
    db.session.commit()
    
    return jsonify(restaurant.to_dict())

@app.route('/restaurants/search', methods=['GET'])
def search_restaurants():
    """Search restaurants with filters: cuisine, min_rating, location"""
    
    # Get query parameters from the URL
    cuisine = request.args.get('cuisine')
    min_rating = request.args.get('min_rating', type=float)
    location = request.args.get('location')
    
    # Start with base query
    query = Restaurant.query
    
    # Apply filters if they exist
    if cuisine:
        query = query.filter(Restaurant.cuisine == cuisine)
    
    if min_rating:
        query = query.filter(Restaurant.rating >= min_rating)
    
    if location:
        # Use ilike for case-insensitive partial matching
        query = query.filter(Restaurant.location.ilike(f'%{location}%'))
    
    # Execute query and get results
    restaurants = query.all()
    
    # Convert to JSON format
    results = [{
        'id': r.id,
        'name': r.name,
        'cuisine': r.cuisine,
        'location': r.location,
        'rating': r.rating
    } for r in restaurants]
    
    return jsonify({
        'count': len(results),
        'restaurants': results
    }), 200
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)