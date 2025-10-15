from client import client
from database.client import Database

if __name__ == "__main__":
    print("Starting bot...")
    Database().init_db()
    client.run()
