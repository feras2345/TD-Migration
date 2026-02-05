#!/usr/bin/env python3
import time
from datetime import datetime
import mysql.connector
import psycopg2
from psycopg2.extras import execute_values

class CDCReplicator:
    def __init__(self):
        self.last_run_timestamp = datetime(2000, 1, 1)
        self.mysql_conn = None
        self.pg_conn = None
        
    def get_mysql_connection(self):
        return mysql.connector.connect(
            host='gt_mysql',
            port=3306,
            user='gt_user',
            password='gt_pass',
            database='globetrotter'
        )
    
    def get_pg_connection(self):
        return psycopg2.connect(
            host='gt_postgres',
            port=5432,
            user='gt_user',
            password='gt_pass',
            database='globetrotter'
        )
    
    def create_pg_table(self):
        """Crée la table dans PostgreSQL si elle n'existe pas"""
        cursor = self.pg_conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id BIGINT PRIMARY KEY,
            customer_email VARCHAR(255) NOT NULL,
            destination VARCHAR(255) NOT NULL,
            departure_date DATE NOT NULL,
            return_date DATE NOT NULL,
            status VARCHAR(50) NOT NULL,
            updated_at TIMESTAMP NOT NULL
        )
        """)
        self.pg_conn.commit()
        print("✅ Table PostgreSQL prête")
    
    def replicate_changes(self):
        """Réplique les changements depuis MySQL vers PostgreSQL"""
        mysql_cursor = self.mysql_conn.cursor(dictionary=True)
        
        # Récupérer les lignes modifiées depuis le dernier passage
        query = """
        SELECT id, customer_email, destination, departure_date, return_date, status, updated_at
        FROM bookings
        WHERE updated_at > %s
        ORDER BY updated_at
        """
        
        mysql_cursor.execute(query, (self.last_run_timestamp,))
        rows = mysql_cursor.fetchall()
        
        if rows:
            pg_cursor = self.pg_conn.cursor()
            
            # Upsert dans PostgreSQL
            upsert_query = """
            INSERT INTO bookings (id, customer_email, destination, departure_date, return_date, status, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                customer_email = EXCLUDED.customer_email,
                destination = EXCLUDED.destination,
                departure_date = EXCLUDED.departure_date,
                return_date = EXCLUDED.return_date,
                status = EXCLUDED.status,
                updated_at = EXCLUDED.updated_at
            """
            
            for row in rows:
                pg_cursor.execute(upsert_query, (
                    row['id'],
                    row['customer_email'],
                    row['destination'],
                    row['departure_date'],
                    row['return_date'],
                    row['status'],
                    row['updated_at']
                ))
                self.last_run_timestamp = max(self.last_run_timestamp, row['updated_at'])
            
            self.pg_conn.commit()
            print(f"🔄 Répliqué {len(rows)} lignes | Dernier timestamp: {self.last_run_timestamp}")
        
        mysql_cursor.close()
    
    def run(self):
        print("🚀 Démarrage du réplicateur CDC...")
        time.sleep(15)  # Attendre que les BDs soient prêtes
        
        self.mysql_conn = self.get_mysql_connection()
        self.pg_conn = self.get_pg_connection()
        self.create_pg_table()
        
        iteration = 0
        while True:
            try:
                self.replicate_changes()
                iteration += 1
                
                if iteration % 10 == 0:
                    # Vérifier la synchronisation
                    mysql_cursor = self.mysql_conn.cursor()
                    pg_cursor = self.pg_conn.cursor()
                    
                    mysql_cursor.execute("SELECT COUNT(*) FROM bookings")
                    mysql_count = mysql_cursor.fetchone()[0]
                    
                    pg_cursor.execute("SELECT COUNT(*) FROM bookings")
                    pg_count = pg_cursor.fetchone()[0]
                    
                    print(f"📊 MySQL: {mysql_count} | PostgreSQL: {pg_count} | Delta: {mysql_count - pg_count}")
                    
                    mysql_cursor.close()
                    pg_cursor.close()
                
                time.sleep(3)  # Vérifier toutes les 3 secondes
                
            except Exception as e:
                print(f"❌ Erreur: {e}")
                time.sleep(5)

if __name__ == "__main__":
    replicator = CDCReplicator()
    replicator.run()
