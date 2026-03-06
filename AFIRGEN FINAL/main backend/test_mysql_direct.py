#!/usr/bin/env python3
"""Direct MySQL connection test with detailed error info"""
import socket
import mysql.connector
from dotenv import load_dotenv
import os

load_dotenv()

host = os.getenv('DB_HOST')
port = int(os.getenv('DB_PORT', 3306))

print(f"Testing connection to {host}:{port}")
print("=" * 60)

# Test 1: TCP socket connection
print("\n1. Testing TCP socket connection...")
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(10)
    result = sock.connect_ex((host, port))
    if result == 0:
        print(f"✓ TCP connection successful to {host}:{port}")
        sock.close()
    else:
        print(f"✗ TCP connection failed with error code: {result}")
        print("  This usually means:")
        print("  - Firewall blocking the connection")
        print("  - Security group not allowing your IP")
        print("  - Network ACL blocking traffic")
except socket.timeout:
    print(f"✗ Connection timed out")
    print("  Your ISP or firewall might be blocking port 3306")
except Exception as e:
    print(f"✗ Socket error: {e}")

# Test 2: MySQL connection
print("\n2. Testing MySQL authentication...")
try:
    conn = mysql.connector.connect(
        host=host,
        port=port,
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME'),
        connection_timeout=10
    )
    print(f"✓ MySQL connection successful!")
    print(f"  Connected to database: {os.getenv('DB_NAME')}")
    conn.close()
except mysql.connector.Error as e:
    print(f"✗ MySQL error: {e}")
    if e.errno == 2003:
        print("  Error 2003: Can't connect to MySQL server")
        print("  This is a network connectivity issue, not authentication")
    elif e.errno == 1045:
        print("  Error 1045: Access denied")
        print("  This means connection works but credentials are wrong")
except Exception as e:
    print(f"✗ Unexpected error: {e}")

print("\n" + "=" * 60)
