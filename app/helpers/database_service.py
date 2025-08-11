import mysql.connector as mysql_conn
import psycopg2
from psycopg2 import sql
import secrets
import string
import re
from types import SimpleNamespace
from config import settings


class SQLInjectionProtector:
    """SQL injection protection and validation class"""
    
    # Valid patterns for different database objects
    DB_NAME_PATTERN = re.compile(r'^[a-zA-Z][a-zA-Z0-9_]{0,63}$')
    USERNAME_PATTERN = re.compile(r'^[a-zA-Z][a-zA-Z0-9_]{0,31}$')
    
    # Dangerous SQL keywords and patterns
    DANGEROUS_PATTERNS = [
        r'(\b(DROP|DELETE|INSERT|UPDATE|ALTER|CREATE|TRUNCATE|EXEC|EXECUTE|UNION|SELECT)\b)',
        r'(--|#|/\*|\*/)',  # SQL comments
        r'(\b(OR|AND)\s+\d+\s*=\s*\d+)',  # Common injection patterns
        r'(\bUNION\s+SELECT\b)',
        r'(\';|\"\;)',  # Statement terminators
    ]
    
    @classmethod
    def validate_identifier(cls, identifier, identifier_type="general"):
        """
        Validate database identifiers
        """
        if not identifier or not isinstance(identifier, str):
            raise ValueError(f"Invalid {identifier_type}: must be a non-empty string")
        
        identifier = identifier.strip()
        
        if identifier_type == "database":
            if not cls.DB_NAME_PATTERN.match(identifier):
                raise ValueError(f"Invalid database name: {identifier}. Must start with letter, contain only alphanumeric and underscore, max 64 chars")
        elif identifier_type == "username":
            if not cls.USERNAME_PATTERN.match(identifier):
                raise ValueError(f"Invalid username: {identifier}. Must start with letter, contain only alphanumeric and underscore, max 32 chars")
        
        # Check for dangerous patterns
        identifier_upper = identifier.upper()
        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, identifier_upper, re.IGNORECASE):
                raise ValueError(f"Potentially dangerous pattern detected in {identifier_type}: {identifier}")
        
        return identifier
    
    @classmethod
    def validate_password(cls, password):
        """
        Validate password - less restrictive but still check for obvious SQL injection
        """
        if not password or not isinstance(password, str):
            raise ValueError("Password must be a non-empty string")
        
        # Check for statement terminators and comment patterns that could be problematic
        dangerous_password_patterns = [
            r'(--|#)',  # SQL comments in passwords are suspicious
            r'(\';|\")',  # Statement terminators
        ]
        
        for pattern in dangerous_password_patterns:
            if re.search(pattern, password):
                raise ValueError("Password contains potentially dangerous characters")
        
        return password
    
    @classmethod
    def sanitize_all_inputs(cls, db_name=None, username=None, password=None):
        """
        Centralized input sanitization for all database operations
        """
        sanitized = {}
        
        if db_name is not None:
            sanitized['db_name'] = cls.validate_identifier(db_name, "database")
        
        if username is not None:
            sanitized['username'] = cls.validate_identifier(username, "username")
        
        if password is not None:
            sanitized['password'] = cls.validate_password(password)
        
        return sanitized


def generate_db_credentials():
    # Use safer character set for passwords - avoid potential SQL metacharacters
    safe_punctuation = r"#%+<=>^_"
    name = ''.join((secrets.choice(string.ascii_letters)
                    for i in range(24)))
    user = ''.join((secrets.choice(string.ascii_letters)
                    for i in range(16)))
    password = ''.join((secrets.choice(
        string.ascii_letters + string.digits + safe_punctuation) for i in range(32)))

    return SimpleNamespace(
        user=user.lower(),
        name=name.lower(),
        password=password
    )


class DatabaseService:

    def __init__(self):
        self.Error = None
        self.protector = SQLInjectionProtector()

    def create_connection(self):
        """ Create a connection to db server """
        pass

    def create_db_connection(self, user=None, password=None, db_name=None):
        """ Create a connection to a single database """
        pass

    def check_user_db_rights(self, user=None, password=None, db_name=None):
        """Verify user rights to db"""
        pass

    # Create or check user exists database
    def create_database(self, db_name=None, user=None, password=None):
        """Create a database with user details"""
        pass

    def check_db_connection(self):
        """Validates if one is able to connect to Database server returns True or False"""
        pass

    # create database user
    def create_user(self, user=None, password=None):
        """ Create a database user with password """
        pass

    # delete database user
    def delete_user(self, user=None):
        """ Delete and existing database user """
        pass

    # delete database
    def delete_database(self, db_name):
        """Deletes database"""
        pass

    def reset_database(self, db_name=None, user=None, password=None):
        """Reset database to initial state"""
        pass

    def get_database_size(self, db_name=None, user=None, password=None):
        """Return size of the database"""
        pass

    # Show all databases
    def get_all_databases(self):
        """Return list of databases"""
        pass

    # Show users
    def get_all_users(self):
        """Return list of users"""
        pass


class MysqlDbService(DatabaseService):
    def __init__(self):
        super().__init__()
        self.Error = mysql_conn.Error

    def create_connection(self):
        try:
            super_connection = mysql_conn.connect(
                host=settings.ADMIN_MYSQL_HOST,
                user=settings.ADMIN_MYSQL_USER,
                password=settings.ADMIN_MYSQL_PASSWORD,
                port=settings.ADMIN_MYSQL_PORT
            )
            return super_connection
        except self.Error as e:
            print(e)
            return False

    def create_db_connection(self, user=None, password=None, db_name=None):
        try:
            # Sanitize inputs
            sanitized = self.protector.sanitize_all_inputs(
                db_name=db_name, username=user, password=password
            )
            
            user_connection = mysql_conn.connect(
                host=settings.ADMIN_MYSQL_HOST,
                user=sanitized['username'],
                password=sanitized['password'],
                port=settings.ADMIN_MYSQL_PORT,
                database=sanitized['db_name']
            )
            return user_connection
        except (self.Error, ValueError) as e:
            print(e)
            return False

    def check_db_connection(self):
        super_connection = None
        try:
            super_connection = self.create_connection()
            if not super_connection:
                return False
            return True
        except self.Error:
            return False
        finally:
            if super_connection and super_connection.is_connected():
                super_connection.close()

    def check_user_db_rights(self, user=None, password=None, db_name=None):
        user_connection = None
        try:
            user_connection = self.create_db_connection(
                user=user, password=password, db_name=db_name)
            if not user_connection:
                return False
            return True
        except (self.Error, ValueError) as e:
            print(e)
            return False
        finally:
            if user_connection and user_connection.is_connected():
                user_connection.close()

    def create_database(self, db_name=None, user=None, password=None):
        connection = None
        cursor = None
        try:
            # Sanitize all inputs
            sanitized = self.protector.sanitize_all_inputs(
                db_name=db_name, username=user, password=password
            )
            
            connection = self.create_connection()
            if not connection:
                return False
            
            cursor = connection.cursor()
            
            # Use parameterized queries where possible, identifiers need to be validated
            cursor.execute(f"CREATE DATABASE `{sanitized['db_name']}`")
            
            if self.create_user(user=user, password=password):
                # Grant privileges using parameterized approach
                grant_query = f"GRANT ALL PRIVILEGES ON `{sanitized['db_name']}`.* TO %s@'%'"
                cursor.execute(grant_query, (sanitized['username'],))
            
            connection.commit()
            return True
        except (self.Error, ValueError) as e:
            print(e)
            return False
        finally:
            if connection and connection.is_connected():
                if cursor:
                    cursor.close()
                connection.close()

    def create_user(self, user=None, password=None):
        connection = None
        cursor = None
        try:
            # Sanitize inputs
            sanitized = self.protector.sanitize_all_inputs(username=user, password=password)
            
            connection = self.create_connection()
            if not connection:
                return False
            
            cursor = connection.cursor()
            
            # Use parameterized query for password, validated identifier for username
            create_user_query = f"CREATE USER `{sanitized['username']}`@'%' IDENTIFIED BY %s"
            cursor.execute(create_user_query, (sanitized['password'],))
            connection.commit()
            return True
        except self.Error as e:
            if e.errno == 1396:  # User already exists
                return True
            print(e)
            return False
        except ValueError as e:
            print(f"Validation error: {e}")
            return False
        finally:
            if connection and connection.is_connected():
                if cursor:
                    cursor.close()
                connection.close()

    def get_database_size(self, db_name=None, user=None, password=None):
        connection = None
        cursor = None
        try:
            sanitized = self.protector.sanitize_all_inputs(
                db_name=db_name, username=user, password=password
            )
            
            connection = self.create_db_connection(
                db_name=db_name, user=user, password=password)
            if not connection:
                return 'N/A'
            
            cursor = connection.cursor()
            
            # Use parameterized query
            size_query = """SELECT table_schema, 
                           SUM(data_length + index_length) / 1024 AS "Size(KB)"
                           FROM information_schema.TABLES 
                           WHERE table_schema = %s
                           GROUP BY table_schema"""
            
            cursor.execute(size_query, (sanitized['db_name'],))
            
            db_size = '0 KB'
            for db in cursor:
                db_size = f'{float(db[1]):.2f} KB'
            return db_size
        except (self.Error, ValueError):
            return 'N/A'
        finally:
            if connection and connection.is_connected():
                if cursor:
                    cursor.close()
                connection.close()

    def reset_password(self, user=None, password=None):
        connection = None
        try:
            sanitized = self.protector.sanitize_all_inputs(username=user, password=password)
            
            connection = self.create_connection()
            if not connection:
                return False
            
            cursor = connection.cursor()
            

            reset_query = f"ALTER USER `{sanitized['username']}`@'%' IDENTIFIED BY %s"
            cursor.execute(reset_query, (sanitized['password'],))
            connection.commit()
            return True
        except (self.Error, ValueError) as e:
            print(e)
            return False
        finally:
            if connection and connection.is_connected():
                cursor.close()
                connection.close()

    def delete_user(self, user=None):
        connection = None
        try:
            sanitized = self.protector.sanitize_all_inputs(username=user)
            
            connection = self.create_connection()
            if not connection:
                return False
            
            cursor = connection.cursor()
            
            # Use validated identifier
            cursor.execute(f"DROP USER `{sanitized['username']}`@'%'")
            connection.commit()
            return True
        except (self.Error, ValueError) as e:
            print(e)
            return False
        finally:
            if connection and connection.is_connected():
                cursor.close()
                connection.close()

    def delete_database(self, db_name):
        connection = None
        try:
            sanitized = self.protector.sanitize_all_inputs(db_name=db_name)
            
            connection = self.create_connection()
            if not connection:
                return False
            
            cursor = connection.cursor()
            cursor.execute(f"DROP DATABASE `{sanitized['db_name']}`")
            # TODO: Need to delete users too
            connection.commit()
            return True
        except (self.Error, ValueError) as e:
            print(e)
            return False
        finally:
            if connection and connection.is_connected():
                cursor.close()
                connection.close()

    def reset_database(self, db_name=None, user=None, password=None):
        connection = None
        cursor = None
        try:
            # Validate inputs first
            sanitized = self.protector.sanitize_all_inputs(
                db_name=db_name, username=user, password=password
            )
            
            connection = self.create_connection()
            user_rights = self.check_user_db_rights(
                db_name=db_name, user=user, password=password)

            if not connection or not user_rights:
                return False
            
            cursor = connection.cursor()
            cursor.execute(f"DROP DATABASE `{sanitized['db_name']}`")
            
            created_db = self.create_database(
                db_name=db_name, user=user, password=password)
            if not created_db:
                return False
            return True
        except (self.Error, ValueError) as e:
            print(e)
            return False
        finally:
            if connection and connection.is_connected():
                if cursor:
                    cursor.close()
                connection.close()

    def get_all_databases(self):
        connection = None
        try:
            connection = self.create_connection()
            if not connection:
                return False
            cursor = connection.cursor()
            cursor.execute("SHOW DATABASES")
            database_list = []
            for db in cursor:
                db_name = db[0]
                if isinstance(db_name, bytes):
                    db_name = db_name.decode()
                database_list.append(db_name)
            return database_list
        except self.Error:
            return False
        finally:
            if connection and connection.is_connected():
                cursor.close()
                connection.close()

    def get_all_users(self):
        connection = None
        try:
            connection = self.create_connection()
            if not connection:
                return False
            cursor = connection.cursor()
            cursor.execute("SELECT user FROM mysql.user GROUP BY user")
            users_list = []
            for db in cursor:
                user_name = db[0]
                if isinstance(user_name, bytes):
                    user_name = user_name.decode()
                users_list.append(user_name)
            return users_list
        except self.Error:
            return False
        finally:
            if connection and connection.is_connected():
                cursor.close()
                connection.close()

    def get_server_status(self):
        connection = None
        try:
            connection = self.create_connection()
            if not connection:
                return {
                    'status': 'error',
                    'message': 'Unable to connect to database'
                }
            cursor = connection.cursor()
            cursor.execute("SHOW GLOBAL STATUS")
            return {
                'status': 'success',
                'data': 'online'
            }
        except self.Error:
            return {
                'status': 'error',
                'message': 'Error has occurred'
            }
        finally:
            if connection and connection.is_connected():
                cursor.close()
                connection.close()

    def disable_user_access(self, db_name, db_user_name):
        connection = None
        try:
            sanitized = self.protector.sanitize_all_inputs(
                db_name=db_name, username=db_user_name
            )
            
            connection = self.create_connection()
            if not connection:
                return False
            cursor = connection.cursor()

            # Revoke all privileges first
            revoke_query = f"REVOKE ALL PRIVILEGES ON `{sanitized['db_name']}`.* FROM `{sanitized['username']}`@'%'"
            cursor.execute(revoke_query)

            # Grant limited privileges
            grant_query = f"GRANT SELECT, DELETE ON `{sanitized['db_name']}`.* TO `{sanitized['username']}`@'%'"
            cursor.execute(grant_query)
            
            connection.commit()
            return True
        except (self.Error, ValueError) as e:
            print(e)
            return False
        finally:
            if connection and connection.is_connected():
                cursor.close()
                connection.close()

    def enable_user_write_access(self, db_name, db_user_name):
        connection = None
        try:
            sanitized = self.protector.sanitize_all_inputs(
                db_name=db_name, username=db_user_name
            )
            
            connection = self.create_connection()
            if not connection:
                return False
            cursor = connection.cursor()
            
            grant_query = f"GRANT ALL PRIVILEGES ON `{sanitized['db_name']}`.* TO `{sanitized['username']}`@'%'"
            cursor.execute(grant_query)
            connection.commit()
            return True
        except (self.Error, ValueError) as e:
            print(e)
            return False
        finally:
            if connection and connection.is_connected():
                cursor.close()
                connection.close()

    def disable_user_log_in(self, db_user_name, db_user_pw):
        connection = None
        try:
            sanitized = self.protector.sanitize_all_inputs(
                username=db_user_name, password=db_user_pw
            )
            
            connection = self.create_connection()
            if not connection:
                return False
            cursor = connection.cursor()
            
            lock_query = f"ALTER USER `{sanitized['username']}`@'%' IDENTIFIED BY %s ACCOUNT LOCK"
            cursor.execute(lock_query, (sanitized['password'],))
            connection.commit()
            return True
        except (self.Error, ValueError) as e:
            print(e)
            return False
        finally:
            if connection and connection.is_connected():
                cursor.close()
                connection.close()

    def enable_user_log_in(self, db_user_name, db_user_pw):
        connection = None
        try:
            sanitized = self.protector.sanitize_all_inputs(
                username=db_user_name, password=db_user_pw
            )
            
            connection = self.create_connection()
            if not connection:
                return False
            cursor = connection.cursor()
            
            unlock_query = f"ALTER USER `{sanitized['username']}`@'%' IDENTIFIED BY %s ACCOUNT UNLOCK"
            cursor.execute(unlock_query, (sanitized['password'],))
            connection.commit()
            return True
        except (self.Error, ValueError) as e:
            print(e)
            return False
        finally:
            if connection and connection.is_connected():
                cursor.close()
                connection.close()


class PostgresqlDbService(DatabaseService):

    def __init__(self):
        super().__init__()
        self.Error = psycopg2.Error

    def create_connection(self):
        try:
            super_connection = psycopg2.connect(
                host=settings.ADMIN_PSQL_HOST,
                user=settings.ADMIN_PSQL_USER,
                password=settings.ADMIN_PSQL_PASSWORD,
                port=settings.ADMIN_PSQL_PORT
            )
            super_connection.autocommit = True
            return super_connection
        except self.Error as e:
            print(e)
            return False

    def check_db_connection(self):
        super_connection = None
        try:
            super_connection = self.create_connection()
            if not super_connection:
                return False
            return True
        except self.Error:
            return False
        finally:
            if super_connection:
                super_connection.close()

    def create_db_connection(self, user=None, password=None, db_name=None):
        try:
            # Sanitize inputs
            sanitized = self.protector.sanitize_all_inputs(
                db_name=db_name, username=user, password=password
            )
            
            user_connection = psycopg2.connect(
                host=settings.ADMIN_PSQL_HOST,
                user=sanitized['username'],
                password=sanitized['password'],
                port=settings.ADMIN_PSQL_PORT,
                database=sanitized['db_name']
            )
            return user_connection
        except (self.Error, ValueError) as e:
            print(e)
            return False

    def check_user_db_rights(self, user=None, password=None, db_name=None):
        user_connection = None
        try:
            user_connection = self.create_db_connection(
                user=user, password=password, db_name=db_name)
            if not user_connection:
                return False
            return True
        except (self.Error, ValueError) as e:
            print(e)
            return False
        finally:
            if user_connection:
                user_connection.close()

    def create_database(self, db_name=None, user=None, password=None):
        connection = None
        try:
            # Sanitize all inputs
            sanitized = self.protector.sanitize_all_inputs(
                db_name=db_name, username=user, password=password
            )
            
            connection = self.create_connection()
            if not connection:
                return False
            cursor = connection.cursor()
            
            if self.create_user(user=user, password=password):
                # Use sql.Identifier for safe identifier handling
                cursor.execute(
                    sql.SQL('CREATE DATABASE {} WITH OWNER = {}').format(
                        sql.Identifier(sanitized['db_name']),
                        sql.Identifier(sanitized['username'])
                    )
                )
            return True
        except (self.Error, ValueError) as e:
            print(e)
            return False
        finally:
            if connection:
                cursor.close()
                connection.close()

    def create_user(self, user=None, password=None):
        connection = None
        try:
            # Sanitize inputs
            sanitized = self.protector.sanitize_all_inputs(username=user, password=password)
            
            connection = self.create_connection()
            if not connection:
                return False
            cursor = connection.cursor()
            
            # Use sql.Identifier and sql.Literal for safe query construction
            cursor.execute(
                sql.SQL('CREATE USER {} WITH ENCRYPTED PASSWORD {}').format(
                    sql.Identifier(sanitized['username']),
                    sql.Literal(sanitized['password'])
                )
            )
            return True
        except self.Error as e:
            print(e)
            if e.pgcode == '42710':  # Duplicate role
                return True
            return False
        except ValueError as e:
            print(f"Validation error: {e}")
            return False
        finally:
            if connection:
                cursor.close()
                connection.close()

    def delete_user(self, user=None):
        connection = None
        try:
            sanitized = self.protector.sanitize_all_inputs(username=user)
            
            connection = self.create_connection()
            if not connection:
                return False
            cursor = connection.cursor()
            
            cursor.execute(
                sql.SQL('DROP USER {}').format(
                    sql.Identifier(sanitized['username'])
                )
            )
            return True
        except self.Error as e:
            if e.pgcode == '42704':  # Undefined object
                return True
            print(e)
            return False
        except ValueError as e:
            print(f"Validation error: {e}")
            return False
        finally:
            if connection:
                cursor.close()
                connection.close()

    def delete_database(self, db_name):
        connection = None
        try:
            sanitized = self.protector.sanitize_all_inputs(db_name=db_name)
            
            connection = self.create_connection()
            if not connection:
                return False
            cursor = connection.cursor()
            
            cursor.execute(
                sql.SQL('DROP DATABASE {}').format(
                    sql.Identifier(sanitized['db_name'])
                )
            )
            return True
        except (self.Error, ValueError) as e:
            print(e)
            return False
        finally:
            if connection:
                cursor.close()
                connection.close()

    def reset_database(self, db_name=None, user=None, password=None):
        connection = None
        cursor = None
        try:
            # Validate inputs first
            sanitized = self.protector.sanitize_all_inputs(
                db_name=db_name, username=user, password=password
            )
            
            connection = self.create_connection()
            user_rights = self.check_user_db_rights(
                db_name=db_name, user=user, password=password)

            if not connection or not user_rights:
                return False
            
            cursor = connection.cursor()
            cursor.execute(
                sql.SQL('DROP DATABASE {}').format(
                    sql.Identifier(sanitized['db_name'])
                )
            )
            
            created_db = self.create_database(
                db_name=db_name, user=user, password=password)
            if not created_db:
                return False
            return True
        except (self.Error, ValueError) as e:
            print(e)
            return False
        finally:
            if connection:
                if cursor:
                    cursor.close()
                connection.close()

    def get_database_size(self, db_name=None, user=None, password=None):
        connection = None
        try:
            sanitized = self.protector.sanitize_all_inputs(
                db_name=db_name, username=user, password=password
            )
            
            connection = self.create_db_connection(
                db_name=db_name, user=user, password=password)
            if not connection:
                return 'N/A'
            cursor = connection.cursor()
            
            # Use parameterized query
            cursor.execute(
                'SELECT pg_size_pretty(pg_database_size(%s))',
                (sanitized['db_name'],)
            )
            
            db_size = '0 bytes'
            for db in cursor:
                db_size = db[0]
            return db_size
        except (self.Error, ValueError):
            return 'N/A'
        finally:
            if connection:
                cursor.close()
                connection.close()

    def get_all_databases(self):
        connection = None
        try:
            connection = self.create_connection()
            if not connection:
                return False
            cursor = connection.cursor()
            cursor.execute("SELECT datname FROM pg_database")
            database_list = []
            for db in cursor:
                database_list.append(db[0])
            return database_list
        except self.Error:
            return False
        finally:
            if connection:
                cursor.close()
                connection.close()

    def get_all_users(self):
        connection = None
        try:
            connection = self.create_connection()
            if not connection:
                return False
            cursor = connection.cursor()
            cursor.execute("SELECT usename FROM pg_catalog.pg_user")
            users_list = []
            for db in cursor:
                users_list.append(db[0])
            return users_list
        except self.Error:
            return False
        finally:
            if connection:
                cursor.close()
                connection.close()

    def reset_password(self, user=None, password=None):
        connection = None
        try:
            sanitized = self.protector.sanitize_all_inputs(username=user, password=password)
            
            connection = self.create_connection()
            if not connection:
                return False
            cursor = connection.cursor()
            
            cursor.execute(
                sql.SQL('ALTER USER {} WITH ENCRYPTED PASSWORD {}').format(
                    sql.Identifier(sanitized['username']),
                    sql.Literal(sanitized['password'])
                )
            )
            return True
        except (self.Error, ValueError) as e:
            print(e)
            return False
        finally:
            if connection:
                cursor.close()
                connection.close()

    def get_server_status(self):
        connection = None
        try:
            connection = self.create_connection()
            if not connection:
                return {
                    'status': 'error',
                    'message': 'Unable to connect to database'
                }
            cursor = connection.cursor()
            cursor.execute("SELECT pg_is_in_recovery()")

            for db in cursor:
                if db[0]:
                    return {
                        'status': 'failed',
                        'message': 'in recovery'
                    }
                else:
                    return {
                        'status': 'success',
                        'message': 'online'
                    }
        except self.Error:
            return {
                'status': 'error',
                'message': 'Error has occurred'
            }
        finally:
            if connection:
                cursor.close()
                connection.close()

    def disable_user_access(self, db_name, db_user_name):
        """Grants read and delete access to the specified user, revoking write and update privileges."""
        connection = None
        try:
            sanitized = self.protector.sanitize_all_inputs(
                db_name=db_name, username=db_user_name
            )
            
            connection = self.create_connection()
            if not connection:
                return False
            cursor = connection.cursor()
            
            # Use sql.Identifier for safe identifier handling
            cursor.execute(
                sql.SQL('REVOKE INSERT, UPDATE ON DATABASE {} FROM {}').format(
                    sql.Identifier(sanitized['db_name']),
                    sql.Identifier(sanitized['username'])
                )
            )
            cursor.execute(
                sql.SQL('REVOKE INSERT, UPDATE ON ALL TABLES IN SCHEMA public FROM {}').format(
                    sql.Identifier(sanitized['username'])
                )
            )
            cursor.execute(
                sql.SQL('REVOKE USAGE ON SCHEMA public FROM {}').format(
                    sql.Identifier(sanitized['username'])
                )
            )
            return True
        except (self.Error, ValueError) as e:
            print(e)
            return False
        finally:
            if connection:
                cursor.close()
                connection.close()

    def enable_user_write_access(self, db_name, db_user_name):
        connection = None
        try:
            sanitized = self.protector.sanitize_all_inputs(
                db_name=db_name, username=db_user_name
            )
            
            connection = self.create_connection()
            if not connection:
                return False
            cursor = connection.cursor()
            
            cursor.execute(
                sql.SQL('GRANT INSERT, UPDATE ON DATABASE {} TO {}').format(
                    sql.Identifier(sanitized['db_name']),
                    sql.Identifier(sanitized['username'])
                )
            )
            cursor.execute(
                sql.SQL('GRANT INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO {}').format(
                    sql.Identifier(sanitized['username'])
                )
            )
            cursor.execute(
                sql.SQL('GRANT USAGE ON SCHEMA public TO {}').format(
                    sql.Identifier(sanitized['username'])
                )
            )
            return True
        except (self.Error, ValueError) as e:
            print(e)
            return False
        finally:
            if connection:
                cursor.close()
                connection.close()

    def disable_user_log_in(self, db_user_name):
        connection = None
        try:
            sanitized = self.protector.sanitize_all_inputs(username=db_user_name)
            
            connection = self.create_connection()
            if not connection:
                return False
            cursor = connection.cursor()
            
            cursor.execute(
                sql.SQL('ALTER USER {} NOLOGIN').format(
                    sql.Identifier(sanitized['username'])
                )
            )
            return True
        except (self.Error, ValueError) as e:
            print(e)
            return False
        finally:
            if connection:
                cursor.close()
                connection.close()

    def enable_user_log_in(self, db_user_name):
        connection = None
        try:
            sanitized = self.protector.sanitize_all_inputs(username=db_user_name)
            
            connection = self.create_connection()
            if not connection:
                return False
            cursor = connection.cursor()
            
            cursor.execute(
                sql.SQL('ALTER USER {} WITH LOGIN').format(
                    sql.Identifier(sanitized['username'])
                )
            )
            return True
        except (self.Error, ValueError) as e:
            print(e)
            return False
        finally:
            if not connection:
                return False
            cursor.close()
            connection.close()
