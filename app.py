from flask import Flask, request, jsonify, render_template
import requests
import os
import pygeohash as geohash

app = Flask(__name__, static_folder='static', template_folder='templates')

TICKETMASTER_API_KEY = os.getenv('TICKETMASTER_API_KEY', 'pVsROiC2NyBNJiGhkZrdKpm8XHFxEWwo')
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY', 'AIzaSyASdpGl9lXM8oKMsytbw4Cpz-qdDFrvQ3g')

CATEGORY_SEGMENTS = {
    'Music': 'KZFzniwnSyZfZ7v7nJ',
    'Sports': 'KZFzniwnSyZfZ7v7nE',
    'Arts': 'KZFzniwnSyZfZ7v7na',
    'Theatre': 'KZFzniwnSyZfZ7v7na',
    'Film': 'KZFzniwnSyZfZ7v7nn',
    'Miscellaneous': 'KZFzniwnSyZfZ7v7n1',
    'Default': None
}

@app.route('/')
def index():
    return render_template('events.html')


@app.route('/api/search')
def search():
    keyword = request.args.get('keyword')
    distance = request.args.get('distance', '10')
    category = request.args.get('category', 'Default')
    geoPoint = request.args.get('geoPoint')
    lat = request.args.get('lat')
    lng = request.args.get('lng')

    segmentId = CATEGORY_SEGMENTS.get(category)

    if not geoPoint and lat and lng:
        geoPoint = geohash.encode(float(lat), float(lng), precision=7)

    params = {
        'apikey': TICKETMASTER_API_KEY,
        'keyword': keyword,
        'radius': distance,
        'unit': 'miles'
    }
    if segmentId:
        params['segmentId'] = segmentId
    if geoPoint:
        params['geoPoint'] = geoPoint

    try:
        r = requests.get('https://app.ticketmaster.com/discovery/v2/events.json', params=params)
        r.raise_for_status()
        data = r.json()

        events = data.get('_embedded', {}).get('events', [])
        return jsonify({
            '_embedded': {'events': events},
            'page': data.get('page', {})
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/event/<event_id>')
def event_details(event_id):
    try:
        r = requests.get(
            f'https://app.ticketmaster.com/discovery/v2/events/{event_id}.json',
            params={'apikey': TICKETMASTER_API_KEY}
        )
        r.raise_for_status()
        return jsonify(r.json())
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/venue_by_keyword')
def venue_by_keyword():
    keyword = request.args.get('keyword')
    try:
        r = requests.get(
            'https://app.ticketmaster.com/discovery/v2/venues.json',
            params={'apikey': TICKETMASTER_API_KEY, 'keyword': keyword}
        )
        r.raise_for_status()
        return jsonify(r.json())
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/geocode')
def geocode():
    address = request.args.get('address')
    if not address:
        return jsonify({'status': 'ERROR', 'message': 'No address provided'}), 400

    try:
        r = requests.get(
            'https://maps.googleapis.com/maps/api/geocode/json',
            params={'address': address, 'key': GOOGLE_API_KEY}
        )
        r.raise_for_status()
        data = r.json()

        if data['status'] == 'OK' and data['results']:
            result = data['results'][0]
            loc = result['geometry']['location']
            formatted_address = result.get('formatted_address')
            address_components = result.get('address_components', [])
            return jsonify({
                'status': 'OK',
                'location': {'lat': loc['lat'], 'lng': loc['lng']},
                'formatted_address': formatted_address,
                'address_components': address_components
            })
        else:
            return jsonify({'status': 'ERROR', 'message': data.get('status', 'Unknown error')}), 400

    except Exception as e:
        return jsonify({'status': 'ERROR', 'message': str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))  # Cloud Run 自动设置
    app.run(host="0.0.0.0", port=port, debug=True)
