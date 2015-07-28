gosu postgres psql --dbname template1 <<EOSQL
    CREATE EXTENSION hstore;
    DROP DATABASE postgres;
    CREATE DATABASE postgres TEMPLATE template1;
EOSQL

