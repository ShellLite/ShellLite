import unittest
import os
from shell_lite.lexer import Lexer
from shell_lite.parser_gbp import GeometricBindingParser
from shell_lite.interpreter import Interpreter

class TestORM(unittest.TestCase):
    def setUp(self):
        self.interpreter = Interpreter()
        for db in ["test_orm.db", "test_orm_comp.db"]:
            if os.path.exists(db):
                try:
                    os.remove(db)
                except PermissionError:
                    pass

    def run_source(self, source):
        lexer = Lexer(source)
        tokens = lexer.tokenize()
        parser = GeometricBindingParser(tokens)
        statements = parser.parse()
        res = None
        for stmt in statements:
            res = self.interpreter.visit(stmt)
        return res

    def test_basic_orm(self):
        source = """
database open "test_orm.db"

model User
    has name as str
    has age as int

create table User

insert User name "Alice" age 25
insert User name "Bob" age 30
insert User name "Charlie" age 35

# Test find all
all_users = find all User
# Test find with where
young_ones = find User where age less than 30
bob = find User where name is "Bob"

# Test update
update User where name is "Alice" set age 26
AliceUpdated = find User where name is "Alice"

# Test delete
delete User where name is "Charlie"
CharlieCheck = find User where name is "Charlie"

database close
"""
        self.run_source(source)
        
        all_users = self.interpreter.global_env.get('all_users')
        self.assertEqual(len(all_users), 3)
        
        young_ones = self.interpreter.global_env.get('young_ones')
        self.assertEqual(len(young_ones), 1)
        self.assertEqual(young_ones[0]['name'], "Alice")
        
        alice_upd = self.interpreter.global_env.get('AliceUpdated')
        self.assertEqual(alice_upd[0]['age'], 26)
        
        charlie_check = self.interpreter.global_env.get('CharlieCheck')
        self.assertEqual(len(charlie_check), 0)
        
        if os.path.exists("test_orm.db"):
            os.remove("test_orm.db")

    def test_orm_complex_conditions(self):
        source = """
database open "test_orm_comp.db"
model Product
    has title as str
    has price as float
create table Product

insert Product title "Phone" price 699.99
insert Product title "Laptop" price 1200.0
insert Product title "Tablet" price 400.0

cheap = find Product where price less than 500
expensive = find Product where price more than 1000

database close
"""
        self.run_source(source)
        self.assertEqual(len(self.interpreter.global_env.get('cheap')), 1)
        self.assertEqual(len(self.interpreter.global_env.get('expensive')), 1)
        
        if os.path.exists("test_orm_comp.db"):
            os.remove("test_orm_comp.db")

if __name__ == '__main__':
    unittest.main()
