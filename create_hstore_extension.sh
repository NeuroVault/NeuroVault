gosu postgres psql --dbname template1 <<EOSQL
    CREATE EXTENSION hstore;
    DROP DATABASE $POSTGRES_USER;
    CREATE DATABASE $POSTGRES_USER TEMPLATE template1;
EOSQL

