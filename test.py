import unittest
from main import app, socketio, rooms, generate_unique_code

class FlaskChatTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        self.ctx = app.app_context()
        self.ctx.push()

    def tearDown(self):
        rooms.clear()
        self.ctx.pop()

    def test_generate_unique_code(self):
        code = generate_unique_code(4)
        self.assertEqual(len(code), 4)
        self.assertNotIn(code, rooms)

    def test_home_get(self):
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)

    def test_create_room(self):
        response = self.app.post('/', data={'name': 'Alice', 'create': 'Create Room'})
        self.assertEqual(response.status_code, 302)

    def test_join_room_valid(self):
        code = generate_unique_code(4)
        rooms[code] = {"members": 0, "messages": []}
        response = self.app.post('/', data={'name': 'Bob', 'code': code, 'join': 'Join'})
        self.assertEqual(response.status_code, 302)

    def test_join_room_invalid(self):
        response = self.app.post('/', data={'name': 'Bob', 'code': 'FAKE', 'join': 'Join'})
        self.assertIn(b'Room does not exist.', response.data)

    def test_missing_name(self):
        response = self.app.post('/', data={'name': '', 'create': 'Create Room'})
        self.assertIn(b'Please enter a name.', response.data)

    def test_join_missing_code(self):
        response = self.app.post('/', data={'name': 'Bob', 'join': 'Join', 'code': ''})
        self.assertIn(b'Please enter a room code.', response.data)

    def test_room_route_invalid(self):
        response = self.app.get('/room', follow_redirects=True)
        self.assertIn(b'html', response.data.lower())

        with self.app.session_transaction() as sess:
            sess['name'] = 'Test'
            sess['room'] = 'FAKE'

        response = self.app.get('/room', follow_redirects=True)
        self.assertIn(b'html', response.data.lower())

    def test_socketio_flow(self):
        room_code = generate_unique_code(4)
        rooms[room_code] = {"members": 0, "messages": []}

        with self.app.session_transaction() as sess:
            sess['name'] = 'Charles'
            sess['room'] = room_code

        client = socketio.test_client(app, flask_test_client=self.app)
        client.emit('join', {})

        # Send
        client.emit('message', {'data': 'Hello'})
        self.assertEqual(len(rooms[room_code]["messages"]), 1)

        message_id = rooms[room_code]["messages"][0]["messageId"]

        # Edit
        client.emit('update_message', {'messageId': message_id, 'newMessage': 'Updated'})
        self.assertTrue(rooms[room_code]["messages"][0]["is_edited"])

        # Delete
        client.emit('delete_message', {'messageId': message_id})
        self.assertEqual(len(rooms[room_code]["messages"]), 0)

        # Edge cases
        client.emit('update_message', {'messageId': '9999', 'newMessage': 'No update'})
        client.emit('delete_message', {'messageId': '9999'})
        with self.app.session_transaction() as sess:
            sess['room'] = 'FAKE'
        client.emit('message', {'data': 'Should not be added'})
        client.disconnect()

if __name__ == '__main__':
    unittest.main()
