#!/usr/bin/env python
"""
Create a sample employees database for testing multi-database support.
"""

import sqlite3
import random
from datetime import datetime, timedelta

def create_employees_db():
    """Create a sample employees database with departments, employees, and projects."""

    conn = sqlite3.connect('employees.db')
    cursor = conn.cursor()

    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON")

    # Create departments table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS department (
        department_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        budget REAL,
        location TEXT
    )
    """)

    # Create employees table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS employee (
        employee_id INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        phone TEXT,
        hire_date DATE NOT NULL,
        job_title TEXT,
        salary REAL,
        department_id INTEGER,
        manager_id INTEGER,
        FOREIGN KEY (department_id) REFERENCES department(department_id),
        FOREIGN KEY (manager_id) REFERENCES employee(employee_id)
    )
    """)

    # Create projects table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS project (
        project_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        start_date DATE,
        end_date DATE,
        budget REAL,
        department_id INTEGER,
        FOREIGN KEY (department_id) REFERENCES department(department_id)
    )
    """)

    # Create employee_project junction table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS employee_project (
        employee_id INTEGER,
        project_id INTEGER,
        role TEXT,
        hours_allocated INTEGER,
        PRIMARY KEY (employee_id, project_id),
        FOREIGN KEY (employee_id) REFERENCES employee(employee_id),
        FOREIGN KEY (project_id) REFERENCES project(project_id)
    )
    """)

    # Insert sample departments
    departments = [
        ('Engineering', 1500000, 'San Francisco'),
        ('Sales', 800000, 'New York'),
        ('Marketing', 600000, 'Los Angeles'),
        ('HR', 400000, 'Chicago'),
        ('Finance', 700000, 'Boston'),
        ('Operations', 900000, 'Seattle')
    ]

    cursor.executemany(
        "INSERT INTO department (name, budget, location) VALUES (?, ?, ?)",
        departments
    )

    # Insert sample employees
    first_names = ['John', 'Jane', 'Michael', 'Sarah', 'David', 'Emily', 'Robert', 'Lisa', 'James', 'Mary']
    last_names = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis', 'Rodriguez', 'Martinez']
    job_titles = ['Software Engineer', 'Senior Engineer', 'Manager', 'Director', 'Analyst', 'Coordinator', 'Specialist', 'Lead', 'Consultant']

    employees = []
    base_date = datetime(2015, 1, 1)

    for i in range(50):
        first_name = random.choice(first_names)
        last_name = random.choice(last_names)
        email = f"{first_name.lower()}.{last_name.lower()}{i}@company.com"
        phone = f"555-{random.randint(1000, 9999)}"
        hire_date = (base_date + timedelta(days=random.randint(0, 2500))).strftime('%Y-%m-%d')
        job_title = random.choice(job_titles)
        salary = random.randint(50000, 200000)
        department_id = random.randint(1, 6)
        # Only some employees have managers (avoid circular references)
        manager_id = random.randint(1, i) if i > 5 and random.random() > 0.3 else None

        employees.append((first_name, last_name, email, phone, hire_date, job_title, salary, department_id, manager_id))

    cursor.executemany("""
        INSERT INTO employee (first_name, last_name, email, phone, hire_date, job_title, salary, department_id, manager_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, employees)

    # Insert sample projects
    project_names = [
        'Website Redesign', 'Mobile App Development', 'Data Migration',
        'Security Audit', 'Marketing Campaign', 'Product Launch',
        'Infrastructure Upgrade', 'Customer Portal', 'Analytics Dashboard',
        'API Development', 'Training Program', 'Cost Reduction Initiative'
    ]

    projects = []
    for i, name in enumerate(project_names):
        description = f"Project for {name.lower()}"
        start_date = (base_date + timedelta(days=random.randint(0, 1000))).strftime('%Y-%m-%d')
        end_date = (datetime.strptime(start_date, '%Y-%m-%d') + timedelta(days=random.randint(30, 365))).strftime('%Y-%m-%d')
        budget = random.randint(50000, 500000)
        department_id = random.randint(1, 6)

        projects.append((name, description, start_date, end_date, budget, department_id))

    cursor.executemany("""
        INSERT INTO project (name, description, start_date, end_date, budget, department_id)
        VALUES (?, ?, ?, ?, ?, ?)
    """, projects)

    # Assign employees to projects
    employee_projects = []
    for project_id in range(1, len(project_names) + 1):
        # Assign 3-8 employees to each project
        num_employees = random.randint(3, 8)
        assigned_employees = random.sample(range(1, 51), num_employees)

        for emp_id in assigned_employees:
            role = random.choice(['Developer', 'Lead', 'Tester', 'Analyst', 'Coordinator'])
            hours = random.randint(20, 160)
            employee_projects.append((emp_id, project_id, role, hours))

    cursor.executemany("""
        INSERT INTO employee_project (employee_id, project_id, role, hours_allocated)
        VALUES (?, ?, ?, ?)
    """, employee_projects)

    # Commit changes
    conn.commit()

    # Print summary
    cursor.execute("SELECT COUNT(*) FROM department")
    dept_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM employee")
    emp_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM project")
    proj_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM employee_project")
    emp_proj_count = cursor.fetchone()[0]

    print("Employees database created successfully!")
    print(f"  - {dept_count} departments")
    print(f"  - {emp_count} employees")
    print(f"  - {proj_count} projects")
    print(f"  - {emp_proj_count} employee-project assignments")

    conn.close()

if __name__ == "__main__":
    create_employees_db()
