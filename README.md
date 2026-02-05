# TD 2 - Migration MySQL → PostgreSQL (Zero Downtime)

## 📋 Description

Simulation d'une migration en ligne de MySQL vers PostgreSQL sans interruption de service pour une plateforme de réservation de voyages (GlobeTrotter).

## 🎯 Objectifs

- Comprendre la différence entre migration "big bang" et migration en ligne
- Mettre en place un pipeline: initial load → réplication des deltas → cutover
- Manipuler MySQL, PostgreSQL, Docker, scripts Python/Faker en ligne de commande

## 🛠️ Technologies

- **MySQL 8** (source)
- **PostgreSQL 16** (cible)
- **Python 3.12** + Faker (génération de trafic)
- **Docker & Docker Compose** (orchestration)
- **CDC maison** (Change Data Capture simplifié)

## 📁 Structure du projet

```
TD-Migration/
├── docker-compose.yml          # Orchestration des services
├── app_faker/
│   └── faker_traffic.py       # Générateur de trafic MySQL
├── app_cdc/
│   └── cdc_replication.py     # Réplicateur CDC MySQL → PostgreSQL
├── scripts/
│   ├── init_mysql.sql         # Initialisation MySQL
│   └── migration_commands.sh  # Commandes de migration
└── README.md
```

## 🚀 Démarrage rapide

### 1. Démarrer l'environnement

```bash
# Lancer tous les services
docker-compose up -d

# Vérifier que les conteneurs tournent
docker-compose ps
```

### 2. Vérifier les connexions

**MySQL:**
```bash
docker exec -it gt_mysql mysql -ugt_user -pgt_pass globetrotter
```

**PostgreSQL:**
```bash
docker exec -it gt_postgres psql -U gt_user -d globetrotter
```

### 3. Vérifier la table bookings

Dans MySQL:
```sql
SHOW TABLES;
DESCRIBE bookings;
SELECT COUNT(*) FROM bookings;
```

### 4. Observer la réplication

```bash
# Logs du générateur de trafic
docker logs -f gt_app_faker

# Logs du réplicateur CDC
docker logs -f gt_app_cdc
```

## 📊 Étapes de migration

### Phase 1: Migration initiale (Bulk)

```bash
# Dump de la table MySQL
docker exec gt_mysql mysqldump -ugt_user -pgt_pass globetrotter bookings > bookings.sql

# Copie vers le conteneur PostgreSQL
docker cp bookings.sql gt_postgres:/tmp/bookings.sql

# Import dans PostgreSQL
docker exec -it gt_postgres psql -U gt_user -d globetrotter -f /tmp/bookings.sql
```

### Phase 2: Réplication continue (CDC)

Le conteneur `app_cdc` tourne en continu et réplique automatiquement:
- Nouvelles insertions
- Mises à jour de status ou dates
- Utilise `updated_at` pour détecter les changements

### Phase 3: Cutover

```bash
# 1. Arrêter le générateur de trafic
docker stop gt_app_faker

# 2. Attendre que CDC réplique tout (vérifier les logs)
docker logs gt_app_cdc

# 3. Comparer les volumes
# MySQL:
docker exec -it gt_mysql mysql -ugt_user -pgt_pass globetrotter -e "SELECT COUNT(*) FROM bookings"

# PostgreSQL:
docker exec -it gt_postgres psql -U gt_user -d globetrotter -c "SELECT COUNT(*) FROM bookings"

# 4. Vérifier les statistiques
docker exec -it gt_mysql mysql -ugt_user -pgt_pass globetrotter -e "SELECT status, COUNT(*) FROM bookings GROUP BY status"
docker exec -it gt_postgres psql -U gt_user -d globetrotter -c "SELECT status, COUNT(*) FROM bookings GROUP BY status"
```

## 🔍 Commandes utiles

### Monitoring

```bash
# Statistiques MySQL
docker exec -it gt_mysql mysql -ugt_user -pgt_pass globetrotter -e "\
SELECT COUNT(*) as total, \
       SUM(CASE WHEN status='confirmed' THEN 1 ELSE 0 END) as confirmed, \
       SUM(CASE WHEN status='pending' THEN 1 ELSE 0 END) as pending, \
       SUM(CASE WHEN status='cancelled' THEN 1 ELSE 0 END) as cancelled \
FROM bookings"

# Statistiques PostgreSQL
docker exec -it gt_postgres psql -U gt_user -d globetrotter -c "\
SELECT COUNT(*) as total, \
       COUNT(*) FILTER (WHERE status='confirmed') as confirmed, \
       COUNT(*) FILTER (WHERE status='pending') as pending, \
       COUNT(*) FILTER (WHERE status='cancelled') as cancelled \
FROM bookings"
```

### Tests de réplication

```bash
# Insérer manuellement dans MySQL
docker exec -it gt_mysql mysql -ugt_user -pgt_pass globetrotter -e "\
INSERT INTO bookings (customer_email, destination, departure_date, return_date, status) \
VALUES ('test@example.com', 'Paris', '2026-03-01', '2026-03-10', 'confirmed')"

# Vérifier dans PostgreSQL après quelques secondes
docker exec -it gt_postgres psql -U gt_user -d globetrotter -c "\
SELECT * FROM bookings WHERE customer_email='test@example.com'"
```

## 🛑 Arrêter l'environnement

```bash
# Arrêter tous les conteneurs
docker-compose down

# Supprimer aussi les volumes (attention: perte de données)
docker-compose down -v
```

## 📝 Rapport d'analyse

### Architecture du flux

```
┌──────────┐         ┌─────────────┐         ┌────────────┐
│  MySQL   │ ──────> │ CDC Script  │ ──────> │ PostgreSQL │
│ (source) │         │ (réplicat.) │         │  (cible)   │
└──────────┘         └─────────────┘         └────────────┘
     ↑                                              ↑
     │                                              │
┌──────────┐                              ┌─────────────┐
│  Faker   │                              │ Initial     │
│ Traffic  │                              │ Bulk Load   │
└──────────┘                              └─────────────┘
```

### Risques de perte de données

1. **Fenêtre de réplication**: Entre deux passages du CDC (3s), des changements peuvent être manqués si `updated_at` est écrasé
2. **Transactions non atomiques**: Si l'application écrit encore sur MySQL après le cutover
3. **Échec du CDC**: Si le script CDC plante, les changements ne sont pas répliqués
4. **Précision du timestamp**: `updated_at` avec précision à la seconde peut causer des collisions

### Améliorations proposées

1. **CDC professionnel**:
   - Debezium avec Kafka pour streaming en temps réel
   - MySQL binlog replication
   - PostgreSQL logical replication

2. **Gestion des transactions**:
   - Verrous applicatifs pendant le cutover
   - Mode lecture seule sur MySQL avant le switch

3. **Validation**:
   - Checksums MD5 sur les données
   - Comparaison ligne par ligne avec tools comme `pt-table-checksum`

4. **Monitoring**:
   - Métriques Prometheus/Grafana
   - Alertes sur le lag de réplication
   - Dashboard temps réel

## 👥 Auteur

Projet TD réalisé dans le cadre de la formation EPSI - DevOps & Database Migration

## 📄 Licence

MIT
