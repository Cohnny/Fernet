import paho.mqtt.client as paho
from cryptography.fernet import Fernet
import random
import threading
import queue
import base64


CLIENT_ID = f'kyh-mqtt-{random.randint(0, 1000)}'
USERNAME = ''
PASSWORD = ''
BROKER = 'broker.hivemq.com'
PORT = 1883

"""
TODO: Skapa en dictionary: namn på chat-rum som mappar till en topic
Ex: python -> kyhchat/group1/python
Skapa tre olika chat-rum
"""
CHAT_ROOMS = {
    'python': 'kyhchat/group1/python/',
    'javascript': 'kyhchat/group2/javascript/',
    'csharp': 'kyhchat/group3/csharp/'
}


class Chat:
    def __init__(self, username, room, key):
        self.username = username
        self.room = room
        self.topic = CHAT_ROOMS[room]
        self.client = None
        self.connect_mqtt()
        self.input_queue = queue.Queue()
        self.cipher = Fernet(key)

        # This variable is used to exit the thread when the
        # user exits the application
        self.running = True

    @staticmethod
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print('Connected to Chat Server. Type "quit" to quit.')
        else:
            print(f'Error connecting to Chat Server. Error code {rc}')

    def connect_mqtt(self):
        # Create a MQTT client object.
        # Every client has an id
        self.client = paho.Client(CLIENT_ID)
        # Set username and password to connect to broker
        self.client.username_pw_set(USERNAME, PASSWORD)

        # When connection response is received from broker
        # call the function on_connect
        self.client.on_connect = self.on_connect

        # Connect to broker
        self.client.connect(BROKER, PORT)

    def on_message(self, client, userdata, message):
        """
        TODO: Implementera: När vi tar emot ett meddelande.

        Avkoda meddelandet (message) och skriv ut det.
        Skriv bara ut meddelandet om det börjar med någon annans användarnamn
        (Dvs. Skriv inte ut meddelanden du själv skickat)
        """
        message = message.payload.decode('utf-8')
        split_message = message.split()

        if split_message[0] == f"<{self.username}>" or split_message[0] == f"*{self.username}":
            return

        # Checks so the list contains at least 2 indexes.
        # Also checks so index 1 isn't the string "has" (cause of the initial <username> has joined msg).
        if len(split_message) >= 2 and split_message[1] != "has":
            # Decrypts index 1 which contains the encrypted message
            decrypted_message = self.cipher.decrypt(split_message[1])
            # Converts the bytes string to utf-8
            decrypted_message_utf8 = decrypted_message.decode()
            # Concatenates the username, whitespace and decrypted message
            print(split_message[0] + " " + decrypted_message_utf8)
        else:
            print(message)

    def init_client(self):
        # Subscribe to selected topic
        self.client.subscribe(self.topic)
        # Set the on_message callback function
        self.client.on_message = self.on_message

        def get_input():
            """
            Function used by the input thread
            :return: None
            """
            while self.running:
                # Get user input and place it in the input_queue
                self.input_queue.put(input())

        # Create input thread
        input_thread = threading.Thread(target=get_input)
        # and start it
        input_thread.start()

        # Start the paho client loop
        self.client.loop_start()

        """
        TODO: Implementera: Skicka ett meddelande till chat-rummet att användaren har anslutit!
        Ex: Andreas has joined the chat
        """
        self.client.publish(self.topic, f"{self.username} has joined the chat")

    def run(self):
        self.init_client()

        while True:
            try:
                # Check if there is an input from the user
                # If not we will get a queue.Empty exception
                msg_to_send = self.input_queue.get_nowait()
                # If we reach this point we have a message

                # Converts from utf-8 to bytes
                msg_to_send_bytes = bytes(msg_to_send, 'utf-8')
                # Encrypts message
                encrypted_message = self.cipher.encrypt(msg_to_send_bytes)

                # Check if the user wants to exit the application
                if msg_to_send.lower() == "quit":

                    """
                    TODO: Implementera: Om användaren vill avsluta ska vi skicka ett meddelande om det.
                    Ex: Andreas has left the chat
                    """
                    self.client.publish(self.topic, f"{self.username} has left the chat")

                    # Indicate to the input thread that it can exit
                    self.running = False
                    break

                """
                TODO: Implementera: Skicka meddelande till chatten.
                Formulera ett meddelande som börjar med användarnamn, följt av meddelandet.
                Skicka sedan meddelandet.
                Ex: <Andreas> Hej alla!
                """
                if msg_to_send.startswith("/me "):
                    msg_to_send = msg_to_send[4:]
                    # self.client.publish(self.topic, f"*{self.username} {msg_to_send}")
                    self.client.publish(self.topic, f"*{self.username} {encrypted_message.decode('utf-8')}")
                else:
                    # Old code
                    # self.client.publish(self.topic, f"<{self.username}> {msg_to_send}")

                    self.client.publish(self.topic, f"<{self.username}> {encrypted_message.decode('utf-8')}")

            except queue.Empty:  # We will end up here if there was no user input
                pass  # No user input, do nothing

        # Stop the paho loop
        self.client.loop_stop()
        # The user needs to press ENTER to exit the while loop in the thread
        print("You have left the chat. Press [ENTER] to exit application.")


def main():
    # Init application. Ask for username and chat room
    username = input("Enter your username: ")

    # Creates 32 bytes key
    key = base64.urlsafe_b64encode(bytes("my32lengthsupersecretnooneknows1", 'utf-8'))

    print("Pick a room:")
    for room in CHAT_ROOMS:
        print(f"\t{room}")
    room = input("> ")

    chat = Chat(username, room, key)
    chat.run()


if __name__ == '__main__':
    main()
