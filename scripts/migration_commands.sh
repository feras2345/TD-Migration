#!/bin/bash
# Script de commandes de migration

echo "=== TD 2 - Migration MySQL → PostgreSQL ==="
echo ""

# Fonction de vérification
check_status() {
    echo "📊 Vérification de la synchronisation..."
    echo ""
    echo "MySQL:"
    docker exec -it gt_mysql mysql -ugt_user -pgt_pass globetrotter -e "SELECT COUNT(*) as total FROM bookings"
    echo ""
    echo "PostgreSQL:"
    docker exec -it gt_postgres psql -U gt_user -d globetrotter -c "SELECT COUNT(*) as total FROM bookings"
}

# Migration initiale
migration_bulk() {
    echo "🔄 Migration initiale (bulk)..."
    docker exec gt_mysql mysqldump -ugt_user -pgt_pass globetrotter bookings > bookings.sql
    docker cp bookings.sql gt_postgres:/tmp/bookings.sql
    docker exec -it gt_postgres psql -U gt_user -d globetrotter -f /tmp/bookings.sql
    echo "✅ Migration bulk terminée"
}

# Cutover
cutover() {
    echo "⚠️  Début du cutover..."
    docker stop gt_app_faker
    echo "Attente de la réplication finale (30s)..."
    sleep 30
    check_status
    echo "✅ Cutover terminé - PostgreSQL est maintenant la base principale"
}

# Menu
case "$1" in
    check)
        check_status
        ;;
    bulk)
        migration_bulk
        ;;
    cutover)
        cutover
        ;;
    *)
        echo "Usage: $0 {check|bulk|cutover}"
        exit 1
        ;;
esac
