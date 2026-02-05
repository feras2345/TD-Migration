#!/usr/bin/env python3
import time
import random
from datetime import datetime, timedelta
from faker import Faker
import mysql.connector

fake = Faker('fr_FR')

def get_mysql_connection():
    return mysql.connector.connect(
        host='gt_mysql',
        port=3306,
        user='gt_user',
        password='gt_pass',
        database='globetrotter'
    )

def insert_booking(cursor):
    """Insère une nouvelle réservation"""
    customer_email = fake.email()
    destination = fake.city()
    departure_date = fake.date_between(start_date='today', end_date='+30d')
    return_date = departure_date + timedelta(days=random.randint(3, 14))
    status = random.choice(['pending', 'confirmed', 'cancelled'])
    
    query = """
    INSERT INTO bookings (customer_email, destination, departure_date, return_date, status)
    VALUES (%s, %s, %s, %s, %s)
    """
    cursor.execute(query, (customer_email, destination, departure_date, return_date, status))
    print(f"[INSERT] Nouvelle réservation: {customer_email} -> {destination}")

def update_random_booking(cursor):
    """Met à jour une réservation existante"""
    cursor.execute("SELECT id FROM bookings ORDER BY RAND() LIMIT 1")
    result = cursor.fetchone()
    
    if result:
        booking_id = result[0]
        new_status = random.choice(['confirmed', 'cancelled', 'completed'])
        
        query = "UPDATE bookings SET status = %s WHERE id = %s"
        cursor.execute(query, (new_status, booking_id))
        print(f"[UPDATE] Réservation {booking_id} -> status: {new_status}")

def main():
    print("🚀 Démarrage du générateur de trafic...")
    time.sleep(10)  # Attendre que MySQL soit prêt
    
    conn = get_mysql_connection()
    cursor = conn.cursor()
    
    # Vérifier/créer la table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bookings (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        customer_email VARCHAR(255) NOT NULL,
        destination VARCHAR(255) NOT NULL,
        departure_date DATE NOT NULL,
        return_date DATE NOT NULL,
        status VARCHAR(50) NOT NULL,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    print("✅ Table bookings prête")
    
    iteration = 0
    while True:
        try:
            # 70% insertions, 30% updates
            if random.random() < 0.7:
                insert_booking(cursor)
            else:
                update_random_booking(cursor)
            
            conn.commit()
            iteration += 1
            
            if iteration % 10 == 0:
                cursor.execute("SELECT COUNT(*) FROM bookings")
                count = cursor.fetchone()[0]
                print(f"📊 Total réservations: {count}")
            
            time.sleep(random.uniform(2, 5))  # 2-5 secondes entre les opérations
            
        except Exception as e:
            print(f"❌ Erreur: {e}")
            conn.rollback()
            time.sleep(5)

if __name__ == "__main__":
    main()
