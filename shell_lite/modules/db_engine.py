import sqlite3
from ..ast_nodes import DatabaseOp, ModelDef, CreateTable, InsertRecord, FindRecords, UpdateRecords, DeleteRecords, String

class DBEngine:
    """
    -----Purpose: Robust engine for handling SQLite operations and ORM logic.
    """
    def __init__(self, interpreter):
        self.interpreter = interpreter
        self.db_conn = None
        self.models = {}

    def visit_DatabaseOp(self, node: DatabaseOp):
        """
        -----Purpose: Handles low-level database operations (open, query, exec, close).
        """
        op = node.op
        args = [self.interpreter.visit(a) for a in node.args]
        
        if op == 'open':
            self.db_conn = sqlite3.connect(args[0])
            self.db_conn.row_factory = sqlite3.Row
            return self.db_conn
        elif op == 'query':
            if not self.db_conn: raise RuntimeError("No database open")
            cursor = self.db_conn.cursor()
            cursor.execute(args[0])
            return [dict(row) for row in cursor.fetchall()]
        elif op == 'exec':
            if not self.db_conn: raise RuntimeError("No database open")
            self.db_conn.execute(args[0])
            self.db_conn.commit()
        elif op == 'close':
            if self.db_conn:
                self.db_conn.close()
                self.db_conn = None

    def visit_ModelDef(self, node: ModelDef):
        """
        -----Purpose: Registers a model definition for the ORM.
        """
        self.models[node.name] = node
        return node

    def visit_CreateTable(self, node: CreateTable):
        """
        -----Purpose: Generates and executes SQL to create a table from a model.
        """
        model = self.models.get(node.model_name)
        if not model:
            raise RuntimeError(f"Model '{node.model_name}' not defined.")
        
        field_defs = ["id INTEGER PRIMARY KEY AUTOINCREMENT"]
        for name, ftype in model.fields:
            sql_type = "TEXT"
            if ftype in ('int', 'integer'): sql_type = "INTEGER"
            elif ftype in ('float', 'number'): sql_type = "REAL"
            field_defs.append(f"{name} {sql_type}")
        
        sql = f"CREATE TABLE IF NOT EXISTS {node.model_name} ({', '.join(field_defs)})"
        return self.visit_DatabaseOp(DatabaseOp('exec', [String(sql)]))

    def visit_InsertRecord(self, node: InsertRecord):
        """
        -----Purpose: Inserts a record into a model-backed table using parameterized queries.
        """
        if not self.db_conn: raise RuntimeError("Database not open")
        fields = [v[0] for v in node.values]
        vals = [self.interpreter.visit(v[1]) for v in node.values]
        placeholders = ", ".join(["?"] * len(vals))
        
        sql = f"INSERT INTO {node.model_name} ({', '.join(fields)}) VALUES ({placeholders})"
        cursor = self.db_conn.cursor()
        cursor.execute(sql, vals)
        self.db_conn.commit()
        return cursor.lastrowid

    def visit_FindRecords(self, node: FindRecords):
        """
        -----Purpose: Executes a 'find' ORM query, optionally performing a COUNT.
        """
        table_name = node.model_name
        sql = f"SELECT {'COUNT(*)' if node.is_count else '*'} FROM {table_name}"
        params = []
        if node.conditions:
            where_clauses = []
            for field, op_name, val_node in node.conditions:
                val = self.interpreter.visit(val_node)
                where_clauses.append(f"{field} {op_name} ?")
                params.append(val)
            sql += " WHERE " + " AND ".join(where_clauses)
        
        if not self.db_conn:
             raise RuntimeError("Database not open")
        c = self.db_conn.cursor()
        c.execute(sql, params)
        if node.is_count:
            res = c.fetchone()
            return res[0] if res else 0
        return [dict(row) for row in c.fetchall()]

    def visit_UpdateRecords(self, node: UpdateRecords):
        """
        -----Purpose: Updates records in a model-backed table.
        """
        if not self.db_conn: raise RuntimeError("Database not open")
        
        set_strs = []
        params = []
        for field, val_node in node.updates:
            val = self.interpreter.visit(val_node)
            set_strs.append(f"{field} = ?")
            params.append(val)
        
        sql = f"UPDATE {node.model_name} SET {', '.join(set_strs)}"
        if node.conditions:
            cond_strs = []
            for field, op, val_node in node.conditions:
                val = self.interpreter.visit(val_node)
                cond_strs.append(f"{field} {op} ?")
                params.append(val)
            sql += f" WHERE {' AND '.join(cond_strs)}"
            
        cursor = self.db_conn.cursor()
        cursor.execute(sql, params)
        self.db_conn.commit()
        return cursor.rowcount

    def visit_DeleteRecords(self, node: DeleteRecords):
        """
        -----Purpose: Deletes records from a model-backed table.
        """
        if not self.db_conn: raise RuntimeError("Database not open")
        
        sql = f"DELETE FROM {node.model_name}"
        params = []
        if node.conditions:
            cond_strs = []
            for field, op, val_node in node.conditions:
                val = self.interpreter.visit(val_node)
                cond_strs.append(f"{field} {op} ?")
                params.append(val)
            sql += f" WHERE {' AND '.join(cond_strs)}"
            
        cursor = self.db_conn.cursor()
        cursor.execute(sql, params)
        self.db_conn.commit()
        return cursor.rowcount
