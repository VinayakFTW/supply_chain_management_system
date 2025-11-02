from flask import Flask,render_template, request, redirect, url_for, session, flash
import mysql.connector as ms
import datetime

def get_db_connection():
    try:
        conn = ms.connect(
            host="localhost",
            user="root",
            password="vini",
            database="smart_supply_chain"
        )
        return conn
    except ms.Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

conn = get_db_connection()
if conn:
    print("MySQL Connection Successful")
    conn.close()
else:
    print("MySQL Connection Failed. Please check credentials and database.")

app = Flask(__name__)
app.secret_key = "kavini"

# --- Helper function for reports ---
def run_report_query(title, query, params=None):
    if 'logged_in' not in session:
        flash('You must be logged in to see this page.')
        return redirect(url_for('login_page'))
    
    conn = get_db_connection()
    if not conn:
        flash("Database connection error.")
        return redirect(url_for('reports'))
    
    results = []
    headers = []
    try:
        cursor = conn.cursor(dictionary=True)
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
            
        results = cursor.fetchall()
        
        if results:
            headers = list(results[0].keys())
            
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error fetching report data: {e}")
        flash(f"An error occurred while fetching report data: {e}")
        
    return render_template('report_view.html', title=title, headers=headers, results=results)

# --- Standard App Routes ---

@app.route('/')
def login_page():
    return render_template('login.html')

@app.route('/login',methods=['POST'])
def login():
    
    email = request.form['email']
    password = request.form['password']
    role = request.form['role']
    
    conn = get_db_connection()
    if not conn:
        flash("Database connection error. Please try again later.")
        return redirect(url_for('login_page'))
    
    cursor = conn.cursor()
    
    query = "SELECT user_id, username, email, user_type FROM users WHERE email = %s AND password = %s AND user_type = %s"    
    cursor.execute(query, (email, password, role))
    
    user = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    if user:
        session['logged_in'] = True
        session['user_id'] = user[0]
        session['username'] = user[1] 
        session['email'] = user[2]
        session['role'] = user[3] 
        
        if session['role'] == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif session['role'] == 'user': 
            return redirect(url_for('user_dashboard'))

    flash('Invalid email, password, or role.')
    return redirect(url_for('login_page'))



@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('role', None)
    session.pop('email', None)
    session.pop('password', None)
    session.pop('username', None)
    session.pop('user_id', None)

    flash('You have been logged out.')
    return redirect(url_for('login_page'))



@app.route('/admin_dashboard')
def admin_dashboard():
    if 'logged_in' not in session or session.get('role') != 'admin':
        flash('You must be logged in as an admin to see this page.')
        return redirect(url_for('login_page'))
    
    return render_template('admin_dashboard.html')


@app.route('/customers')
def customers():
    if 'logged_in' not in session or session.get('role') != 'admin':
        flash('You must be logged in as an admin to see this page.')
        return redirect(url_for('login_page'))

    search_customer_id = request.args.get('customer_id', '')    
    search_name = request.args.get('name', '')
    search_address = request.args.get('address', '')
    search_contact = request.args.get('contact', '')

    customer_list = []
    conn = get_db_connection()
    if not conn:
        flash("Database connection error.")
        return render_template('customers.html', **locals())

    try:
        cursor = conn.cursor(dictionary=True)
        query = "SELECT Customer_ID, Name, Address, Contact FROM customers"
        
        where_clauses = []
        params = []
        
        if search_customer_id:
            where_clauses.append("Customer_ID = %s")
            params.append(f"{search_customer_id}")
        if search_name:
            where_clauses.append("Name LIKE %s")
            params.append(f"%{search_name}%")
        if search_address:
            where_clauses.append("Address LIKE %s")
            params.append(f"%{search_address}%")
        if search_contact:
            where_clauses.append("Contact LIKE %s")
            params.append(f"%{search_contact}%")

        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
            
        query += " ORDER BY Customer_ID"
        cursor.execute(query, tuple(params))
        customer_list = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Error fetching customer data: {e}")
        flash(f"An error occurred while fetching customer data: {e}")
    
    return render_template('customers.html', 
                           customers=customer_list,
                           search_customer_id=search_customer_id,
                           search_name=search_name,
                           search_address=search_address,
                           search_contact=search_contact)


@app.route('/orders')
def orders():
    if 'logged_in' not in session:
        flash('You must be logged in to see this page.')
        return redirect(url_for('login_page'))
        
    role = session.get('role')
    user_id = session.get('user_id')
    
    search_order_id = request.args.get('order_id', '')
    search_customer_name = request.args.get('customer_name', '')
    search_status = request.args.get('status', '')
    
    order_list = []
    conn = get_db_connection()
    if not conn:
        flash("Database connection error.")
        return render_template('orders.html', **locals())

    try:
        cursor = conn.cursor(dictionary=True)
        
        query = """
            SELECT 
                O.Order_ID, 
                C.Name AS customer_name, 
                O.Date, 
                O.Status
            FROM orders O
            JOIN customers C ON O.Customer_ID = C.Customer_ID
        """
        
        where_clauses = []
        params = []
        
        if role == 'user':
            where_clauses.append("O.Customer_ID = %s")
            params.append(user_id) 
                
        if search_order_id:
            where_clauses.append("O.Order_ID = %s")
            params.append(f"{search_order_id}")
        if search_customer_name:
            where_clauses.append("C.Name LIKE %s")
            params.append(f"%{search_customer_name}%")
        if search_status:
            where_clauses.append("O.Status = %s")
            params.append(search_status)
        
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
            
        query += " ORDER BY O.Date DESC"
        cursor.execute(query, tuple(params))
        order_list = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Error fetching order data: {e}")
        flash(f"An error occurred while fetching order data: {e}")
    
    return render_template('orders.html', 
                           orders=order_list, 
                           search_order_id=search_order_id, 
                           search_customer_name=search_customer_name,
                           search_status=search_status)

@app.route('/invoices')
def invoices():
    if 'logged_in' not in session:
        flash('You must be logged in to see this page.')
        return redirect(url_for('login_page'))
        
    role = session.get('role')
    user_id = session.get('user_id')
    
    search_invoice_id = request.args.get('invoice_id', '')
    search_order_id = request.args.get('order_id', '')
    search_customer_name = request.args.get('customer_name', '')
    search_status = request.args.get('status', '')
    
    invoice_list = []
    conn = get_db_connection()
    if not conn:
        flash("Database connection error.")
        return render_template('invoices.html', **locals())

    try:
        cursor = conn.cursor(dictionary=True)
        
        query = """
            SELECT 
                I.Invoice_ID, I.Order_ID,
                C.Name AS customer_name,
                I.Amount, I.Due_Date, I.Status
            FROM invoices I
            JOIN orders O ON I.Order_ID = O.Order_ID
            JOIN customers C ON O.Customer_ID = C.Customer_ID
        """
        
        where_clauses = []
        params = []
        
        if role == 'user':
            where_clauses.append("O.Customer_ID = %s")
            params.append(user_id)
                
        if search_invoice_id:
            where_clauses.append("I.Invoice_ID = %s")
            params.append(f"{search_invoice_id}")
        if search_order_id:
            where_clauses.append("I.Order_ID = %s")
            params.append(f"{search_order_id}")
        if search_customer_name:
            where_clauses.append("C.Name LIKE %s")
            params.append(f"%{search_customer_name}%")
        if search_status:
            where_clauses.append("I.Status = %s")
            params.append(search_status)
        
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
            
        query += " ORDER BY I.Due_Date DESC"
        cursor.execute(query, tuple(params))
        invoice_list = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Error fetching invoice data: {e}")
        flash(f"An error occurred while fetching invoice data: {e}")
    
    return render_template('invoices.html', 
                           invoices=invoice_list,
                           search_invoice_id=search_invoice_id,
                           search_order_id=search_order_id,
                           search_customer_name=search_customer_name,
                           search_status=search_status)


@app.route('/user_dashboard')
def user_dashboard():
    if 'logged_in' not in session:
        flash('You must be logged in as a user to see this page.')
        return redirect(url_for('login_page'))
    
    active_orders_count = 0
    total_invoiced = 0
    total_paid = 0
    status_chart_data = {'labels': [], 'data': []}
    
    user_id = session.get('user_id')
    role = session.get('role')

    conn = get_db_connection()
    if not conn:
        flash("Database connection error.")
        return render_template('user_dashboard.html', **locals())
    
    try:
        cursor = conn.cursor()
        
        if role == 'user':
            query1 = "SELECT COUNT(Order_ID) FROM orders WHERE status = 'Processing' AND Customer_ID = %s"
            cursor.execute(query1, (user_id,))
            result = cursor.fetchone()
            if result: active_orders_count = result[0]
    
            query2 = "SELECT SUM(I.Amount) FROM invoices I JOIN orders O ON I.Order_ID = O.Order_ID WHERE O.Customer_ID = %s"
            cursor.execute(query2, (user_id,))
            result = cursor.fetchone()
            if result and result[0] is not None: total_invoiced = float(result[0])
            
            query3 = "SELECT SUM(I.Amount) FROM invoices I JOIN orders O ON I.Order_ID = O.Order_ID WHERE I.Status = 'Paid' AND O.Customer_ID = %s"
            cursor.execute(query3, (user_id,))
            result = cursor.fetchone()
            if result and result[0] is not None: total_paid = float(result[0])
            
            query_status = "SELECT Status, COUNT(Order_ID) FROM orders WHERE Customer_ID = %s GROUP BY Status"
            cursor.execute(query_status, (user_id,))
            
        else:
            query_status = "SELECT 1, 0 WHERE 1=0" 
            cursor.execute(query_status)

        status_results = cursor.fetchall()
        if status_results:
            labels = []
            data = []
            for row in status_results:
                labels.append(str(row[0]).capitalize())
                data.append(row[1])
            status_chart_data = {'labels': labels, 'data': data}

    except Exception as e:
        print(f"Error fetching dashboard data: {e}")
        flash("An error occurred while fetching dashboard data.")
    finally:
        if 'cursor' in locals() and cursor:
            cursor.close()
        if 'conn' in locals() and conn.is_connected():
            conn.close()

    return render_template('user_dashboard.html', 
                            active_orders=active_orders_count, 
                            total_invoiced=total_invoiced, 
                            total_paid=total_paid,
                            status_data=status_chart_data)
    

@app.route('/reports')
def reports():
    if 'logged_in' not in session:
        flash('You must be logged in to see this page.')
        return redirect(url_for('login_page'))
    
    return render_template('reports.html')

# --- Management Routes ---

@app.route('/products')
def products():
    if 'logged_in' not in session or session.get('role') != 'admin':
        flash('You must be logged in as an admin to see this page.')
        return redirect(url_for('login_page'))

    search_name = request.args.get('search_name', '')
    search_sku = request.args.get('search_sku', '')
    search_manufacturer = request.args.get('search_manufacturer', '')
    
    product_list = []
    conn = get_db_connection()
    if not conn:
        flash("Database connection error.")
        return render_template('products.html', products=product_list, **locals())

    try:
        cursor = conn.cursor(dictionary=True)
        query = """
            SELECT 
                P.Product_ID, P.Name, P.Description, P.SKU, M.Name AS Manufacturer_Name
            FROM products P
            LEFT JOIN manufacturers M ON P.Manufacturer_ID = M.Manufacturer_ID
        """
        
        where_clauses = []
        params = []
        
        if search_name:
            where_clauses.append("P.Name LIKE %s")
            params.append(f"%{search_name}%")
        if search_sku:
            where_clauses.append("P.SKU LIKE %s")
            params.append(f"%{search_sku}%")
        if search_manufacturer:
            where_clauses.append("M.Name LIKE %s")
            params.append(f"%{search_manufacturer}%")

        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
            
        query += " ORDER BY P.Product_ID"
        cursor.execute(query, tuple(params))
        product_list = cursor.fetchall()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error fetching product data: {e}")
        flash(f"An error occurred while fetching product data: {e}")
    
    return render_template('products.html', products=product_list, **locals())


@app.route('/suppliers')
def suppliers():
    if 'logged_in' not in session or session.get('role') != 'admin':
        flash('You must be logged in as an admin to see this page.')
        return redirect(url_for('login_page'))

    search_name = request.args.get('search_name', '')
    search_contact = request.args.get('search_contact', '')
    
    supplier_list = []
    conn = get_db_connection()
    if not conn:
        flash("Database connection error.")
        return render_template('suppliers.html', suppliers=supplier_list, **locals())

    try:
        cursor = conn.cursor(dictionary=True)
        query = "SELECT Supplier_ID, Name, Contact, Address FROM suppliers"
        
        where_clauses = []
        params = []
        
        if search_name:
            where_clauses.append("Name LIKE %s")
            params.append(f"%{search_name}%")
        if search_contact:
            where_clauses.append("Contact LIKE %s")
            params.append(f"%{search_contact}%")

        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
            
        query += " ORDER BY Supplier_ID"
        cursor.execute(query, tuple(params))
        supplier_list = cursor.fetchall()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error fetching supplier data: {e}")
        flash(f"An error occurred while fetching supplier data: {e}")
    
    return render_template('suppliers.html', suppliers=supplier_list, **locals())


@app.route('/manufacturers')
def manufacturers():
    if 'logged_in' not in session or session.get('role') != 'admin':
        flash('You must be logged in as an admin to see this page.')
        return redirect(url_for('login_page'))

    search_name = request.args.get('search_name', '')
    search_contact = request.args.get('search_contact', '')

    manufacturer_list = []
    conn = get_db_connection()
    if not conn:
        flash("Database connection error.")
        return render_template('manufacturers.html', manufacturers=manufacturer_list, **locals())

    try:
        cursor = conn.cursor(dictionary=True)
        query = "SELECT Manufacturer_ID, Name, Contact, Address FROM manufacturers"
        
        where_clauses = []
        params = []
        
        if search_name:
            where_clauses.append("Name LIKE %s")
            params.append(f"%{search_name}%")
        if search_contact:
            where_clauses.append("Contact LIKE %s")
            params.append(f"%{search_contact}%")

        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
            
        query += " ORDER BY Manufacturer_ID"
        
        cursor.execute(query, tuple(params))
        manufacturer_list = cursor.fetchall()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error fetching manufacturer data: {e}")
        flash(f"An error occurred while fetching manufacturer data: {e}")
    
    return render_template('manufacturers.html', manufacturers=manufacturer_list, **locals())


@app.route('/warehouses')
def warehouses():
    if 'logged_in' not in session or session.get('role') != 'admin':
        flash('You must be logged in as an admin to see this page.')
        return redirect(url_for('login_page'))

    search_name = request.args.get('search_name', '')
    search_location = request.args.get('search_location', '')

    warehouse_list = []
    conn = get_db_connection()
    if not conn:
        flash("Database connection error.")
        return render_template('warehouses.html', warehouses=warehouse_list, **locals())

    try:
        cursor = conn.cursor(dictionary=True)
        query = "SELECT Warehouse_ID, Name, Location, Capacity FROM warehouses"
        
        where_clauses = []
        params = []
        
        if search_name:
            where_clauses.append("Name LIKE %s")
            params.append(f"%{search_name}%")
        if search_location:
            where_clauses.append("Location LIKE %s")
            params.append(f"%{search_location}%")

        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
            
        query += " ORDER BY Warehouse_ID"
        
        cursor.execute(query, tuple(params))
        warehouse_list = cursor.fetchall()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error fetching warehouse data: {e}")
        flash(f"An error occurred while fetching warehouse data: {e}")
    
    return render_template('warehouses.html', warehouses=warehouse_list, **locals())


@app.route('/vehicles')
def vehicles():
    if 'logged_in' not in session or session.get('role') != 'admin':
        flash('You must be logged in as an admin to see this page.')
        return redirect(url_for('login_page'))

    search_type = request.args.get('search_type', '')
    search_license = request.args.get('search_license', '')
    search_status = request.args.get('search_status', '')

    vehicle_list = []
    conn = get_db_connection()
    if not conn:
        flash("Database connection error.")
        return render_template('vehicles.html', vehicles=vehicle_list, **locals())

    try:
        cursor = conn.cursor(dictionary=True)
        query = "SELECT Vehicle_ID, Type, License_Plate, Capacity, Status FROM vehicles"
        
        where_clauses = []
        params = []
        
        if search_type:
            where_clauses.append("Type LIKE %s")
            params.append(f"%{search_type}%")
        if search_license:
            where_clauses.append("License_Plate LIKE %s")
            params.append(f"%{search_license}%")
        if search_status:
            where_clauses.append("Status LIKE %s")
            params.append(f"%{search_status}%")

        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
            
        query += " ORDER BY Vehicle_ID"
        
        cursor.execute(query, tuple(params))
        vehicle_list = cursor.fetchall()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error fetching vehicle data: {e}")
        flash(f"An error occurred while fetching vehicle data: {e}")
    
    return render_template('vehicles.html', vehicles=vehicle_list, **locals())

# ---------------------------------------------------------------
# ---  ADD ROUTES START HERE ---
# ---------------------------------------------------------------

@app.route('/add/customer', methods=['GET', 'POST'])
def add_customer():
    if 'logged_in' not in session or session.get('role') != 'admin':
        flash('You do not have permission to access this page.')
        return redirect(url_for('login_page'))

    if request.method == 'POST':
        try:
            customer_id = request.form['customer_id']
            name = request.form['name']
            address = request.form['address']
            contact = request.form['contact']
            
            conn = get_db_connection()
            cursor = conn.cursor()
            query = "INSERT INTO customers (Customer_ID, Name, Address, Contact) VALUES (%s, %s, %s, %s)"
            cursor.execute(query, (customer_id, name, address, contact))
            conn.commit()
            cursor.close()
            conn.close()
            
            flash('New customer created successfully!', 'success')
            return redirect(url_for('customers'))

        except ms.Error as e:
            flash(f'Database error: {e.msg}', 'error')
        except Exception as e:
            flash(f'Error creating customer: {e}', 'error')
        
        return redirect(url_for('add_customer'))

    return render_template('add_customer.html')

@app.route('/add/product', methods=['GET', 'POST'])
def add_product():
    if 'logged_in' not in session or session.get('role') != 'admin':
        flash('You do not have permission to access this page.')
        return redirect(url_for('login_page'))

    if request.method == 'POST':
        try:
            product_id = request.form['product_id']
            name = request.form['name']
            description = request.form['description']
            sku = request.form['sku']
            manufacturer_id = request.form['manufacturer_id']
            
            conn = get_db_connection()
            cursor = conn.cursor()
            query = "INSERT INTO products (Product_ID, Name, Description, SKU, Manufacturer_ID) VALUES (%s, %s, %s, %s, %s)"
            cursor.execute(query, (product_id, name, description, sku, manufacturer_id))
            conn.commit()
            cursor.close()
            conn.close()
            
            flash('New product created successfully!', 'success')
            return redirect(url_for('products'))

        except ms.Error as e:
            flash(f'Database error: {e.msg}', 'error')
        except Exception as e:
            flash(f'Error creating product: {e}', 'error')
        
        return redirect(url_for('add_product'))

    # GET Request: Fetch manufacturers for the dropdown
    manufacturers_list = []
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT Manufacturer_ID, Name FROM manufacturers")
        manufacturers_list = cursor.fetchall()
        cursor.close()
        conn.close()
    except Exception as e:
        flash(f'Error fetching manufacturers: {e}', 'error')
        
    return render_template('add_product.html', manufacturers=manufacturers_list)

@app.route('/add/supplier', methods=['GET', 'POST'])
def add_supplier():
    if 'logged_in' not in session or session.get('role') != 'admin':
        flash('You do not have permission to access this page.')
        return redirect(url_for('login_page'))

    if request.method == 'POST':
        try:
            supplier_id = request.form['supplier_id']
            name = request.form['name']
            address = request.form['address']
            contact = request.form['contact']
            
            conn = get_db_connection()
            cursor = conn.cursor()
            query = "INSERT INTO suppliers (Supplier_ID, Name, Address, Contact) VALUES (%s, %s, %s, %s)"
            cursor.execute(query, (supplier_id, name, address, contact))
            conn.commit()
            cursor.close()
            conn.close()
            
            flash('New supplier created successfully!', 'success')
            return redirect(url_for('suppliers'))

        except ms.Error as e:
            flash(f'Database error: {e.msg}', 'error')
        except Exception as e:
            flash(f'Error creating supplier: {e}', 'error')
        
        return redirect(url_for('add_supplier'))

    return render_template('add_supplier.html')

@app.route('/add/manufacturer', methods=['GET', 'POST'])
def add_manufacturer():
    if 'logged_in' not in session or session.get('role') != 'admin':
        flash('You do not have permission to access this page.')
        return redirect(url_for('login_page'))

    if request.method == 'POST':
        try:
            manufacturer_id = request.form['manufacturer_id']
            name = request.form['name']
            address = request.form['address']
            contact = request.form['contact']
            
            conn = get_db_connection()
            cursor = conn.cursor()
            query = "INSERT INTO manufacturers (Manufacturer_ID, Name, Address, Contact) VALUES (%s, %s, %s, %s)"
            cursor.execute(query, (manufacturer_id, name, address, contact))
            conn.commit()
            cursor.close()
            conn.close()
            
            flash('New manufacturer created successfully!', 'success')
            return redirect(url_for('manufacturers'))

        except ms.Error as e:
            flash(f'Database error: {e.msg}', 'error')
        except Exception as e:
            flash(f'Error creating manufacturer: {e}', 'error')
        
        return redirect(url_for('add_manufacturer'))

    return render_template('add_manufacturer.html')

@app.route('/add/warehouse', methods=['GET', 'POST'])
def add_warehouse():
    if 'logged_in' not in session or session.get('role') != 'admin':
        flash('You do not have permission to access this page.')
        return redirect(url_for('login_page'))

    if request.method == 'POST':
        try:
            warehouse_id = request.form['warehouse_id']
            name = request.form['name']
            location = request.form['location']
            capacity = request.form['capacity']
            
            conn = get_db_connection()
            cursor = conn.cursor()
            query = "INSERT INTO warehouses (Warehouse_ID, Name, Location, Capacity) VALUES (%s, %s, %s, %s)"
            cursor.execute(query, (warehouse_id, name, location, capacity))
            conn.commit()
            cursor.close()
            conn.close()
            
            flash('New warehouse created successfully!', 'success')
            return redirect(url_for('warehouses'))

        except ms.Error as e:
            flash(f'Database error: {e.msg}', 'error')
        except Exception as e:
            flash(f'Error creating warehouse: {e}', 'error')
        
        return redirect(url_for('add_warehouse'))

    return render_template('add_warehouse.html')

@app.route('/add/vehicle', methods=['GET', 'POST'])
def add_vehicle():
    if 'logged_in' not in session or session.get('role') != 'admin':
        flash('You do not have permission to access this page.')
        return redirect(url_for('login_page'))

    if request.method == 'POST':
        try:
            vehicle_id = request.form['vehicle_id']
            v_type = request.form['type']
            license_plate = request.form['license_plate']
            capacity = request.form['capacity']
            status = request.form['status']
            
            conn = get_db_connection()
            cursor = conn.cursor()
            query = "INSERT INTO vehicles (Vehicle_ID, Type, License_Plate, Capacity, Status) VALUES (%s, %s, %s, %s, %s)"
            cursor.execute(query, (vehicle_id, v_type, license_plate, capacity, status))
            conn.commit()
            cursor.close()
            conn.close()
            
            flash('New vehicle created successfully!', 'success')
            return redirect(url_for('vehicles'))

        except ms.Error as e:
            flash(f'Database error: {e.msg}', 'error')
        except Exception as e:
            flash(f'Error creating vehicle: {e}', 'error')
        
        return redirect(url_for('add_vehicle'))

    return render_template('add_vehicle.html')


@app.route('/add/order', methods=['GET', 'POST'])
def add_order():
    if 'logged_in' not in session or session.get('role') != 'admin':
        flash('You do not have permission to access this page.')
        return redirect(url_for('login_page'))

    conn = get_db_connection()
    if not conn:
        flash("Database connection error.")
        return redirect(url_for('orders'))

    if request.method == 'POST':
        try:
            order_id = request.form['order_id']
            customer_id = request.form['customer_id']
            order_date = request.form['order_date']
            status = request.form['status']
            product_id = request.form['product_id']
            quantity = request.form['quantity']

            cursor = conn.cursor()
            
            # --- Start Transaction ---
            conn.start_transaction()
            
            # 1. Insert into orders table
            query_order = "INSERT INTO orders (Order_ID, Customer_ID, Date, Status) VALUES (%s, %s, %s, %s)"
            cursor.execute(query_order, (order_id, customer_id, order_date, status))
            
            # 2. Insert into order_items table
            query_item = "INSERT INTO order_items (Order_ID, Product_ID, Quantity) VALUES (%s, %s, %s)"
            cursor.execute(query_item, (order_id, product_id, quantity))
            
            # --- Commit Transaction ---
            conn.commit()
            
            flash('New order created successfully!', 'success')
            return redirect(url_for('orders'))

        except ms.Error as e:
            conn.rollback()
            flash(f'Database error: {e.msg}', 'error')
        except Exception as e:
            conn.rollback()
            flash(f'Error creating order: {e}', 'error')
        finally:
            cursor.close()
            conn.close()
        
        return redirect(url_for('add_order'))

    customers_list = []
    products_list = []
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Get customers
        cursor.execute("SELECT Customer_ID, Name FROM customers ORDER BY Name")
        customers_list = cursor.fetchall()
        
        # Get products
        cursor.execute("SELECT Product_ID, Name FROM products ORDER BY Name")
        products_list = cursor.fetchall()
        
    except Exception as e:
        flash(f'Error fetching data: {e}', 'error')
    finally:
        if 'cursor' in locals() and cursor:
            cursor.close()
        conn.close()
        
    return render_template('add_order.html', customers=customers_list, products=products_list)


@app.route('/add/invoice', methods=['GET', 'POST'])
def add_invoice():
    if not check_admin(): return redirect(url_for('login_page'))

    conn = get_db_connection()
    if not conn:
        flash("Database connection error.")
        return redirect(url_for('invoices'))

    if request.method == 'POST':
        try:
            invoice_id = request.form['invoice_id']
            order_id = request.form['order_id']
            amount = request.form['amount']
            due_date = request.form['due_date']
            status = request.form['status']

            cursor = conn.cursor()
            query = "INSERT INTO invoices (Invoice_ID, Order_ID, Amount, Due_Date, Status) VALUES (%s, %s, %s, %s, %s)"
            cursor.execute(query, (invoice_id, order_id, amount, due_date, status))
            conn.commit()
            
            flash('New invoice created successfully!', 'success')
            return redirect(url_for('invoices'))

        except ms.Error as e:
            conn.rollback() 
            flash(f'Database error: {e.msg}', 'error')
        except Exception as e:
            conn.rollback()
            flash(f'Error creating invoice: {e}', 'error')
        finally:
            if 'cursor' in locals() and cursor:
                cursor.close()
            conn.close()
        
        return redirect(url_for('add_invoice'))

    # --- GET Request: Fetch orders for dropdown ---
    orders_list = []
    try:
        cursor = conn.cursor(dictionary=True)
        # Fetch orders that might not have an invoice yet
        cursor.execute("SELECT Order_ID, Customer_ID FROM orders ORDER BY Order_ID DESC")
        orders_list = cursor.fetchall()
    except Exception as e:
        flash(f'Error fetching orders: {e}', 'error')
    finally:
        if 'cursor' in locals() and cursor:
            cursor.close()
        conn.close()
        
    return render_template('add_invoice.html', orders=orders_list)

# ---------------------------------------------------------------
# --- EDIT / UPDATE ROUTES START HERE ---
# ---------------------------------------------------------------

@app.route('/edit/invoice/<int:id>', methods=['GET'])
def edit_invoice(id):
    if not check_admin(): return redirect(url_for('login_page'))
    
    conn = get_db_connection()
    if not conn:
        flash("Database connection error.")
        return redirect(url_for('invoices'))
        
    invoice = None
    orders_list = []
    try:
        cursor = conn.cursor(dictionary=True)
        
        # 1. Get the specific invoice
        cursor.execute("SELECT * FROM invoices WHERE Invoice_ID = %s", (id,))
        invoice = cursor.fetchone()
        
        # 2. Get all orders for the dropdown
        cursor.execute("SELECT Order_ID, Customer_ID FROM orders ORDER BY Order_ID DESC")
        orders_list = cursor.fetchall()
        
        cursor.close()
        conn.close()
    except Exception as e:
        flash(f'Error fetching invoice data: {e}', 'error')
        return redirect(url_for('invoices'))
        
    if not invoice:
        flash('Invoice not found.', 'error')
        return redirect(url_for('invoices'))
        
    if invoice['Due_Date']:
        invoice['Due_Date'] = invoice['Due_Date'].strftime('%Y-%m-%d')
        
    return render_template('edit_invoice.html', invoice=invoice, orders=orders_list)

@app.route('/update/invoice/<int:id>', methods=['POST'])
def update_invoice(id):
    if not check_admin(): return redirect(url_for('login_page'))
    
    try:
        order_id = request.form['order_id']
        amount = request.form['amount']
        due_date = request.form['due_date']
        status = request.form['status']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        query = """
            UPDATE invoices 
            SET Order_ID = %s, Amount = %s, Due_Date = %s, Status = %s 
            WHERE Invoice_ID = %s
        """
        cursor.execute(query, (order_id, amount, due_date, status, id))
        conn.commit()
        cursor.close()
        conn.close()
        
        flash('Invoice updated successfully!', 'success')
    except ms.Error as e:
        flash(f'Database error: {e.msg}', 'error')
    except Exception as e:
        flash(f'Error updating invoice: {e}', 'error')
        
    return redirect(url_for('invoices'))


@app.route('/edit/customer/<int:id>', methods=['GET'])
def edit_customer(id):
    if not check_admin(): return redirect(url_for('login_page'))
    
    conn = get_db_connection()
    if not conn:
        flash("Database connection error.")
        return redirect(url_for('customers'))
        
    customer = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM customers WHERE Customer_ID = %s", (id,))
        customer = cursor.fetchone()
        cursor.close()
        conn.close()
    except Exception as e:
        flash(f'Error fetching customer data: {e}', 'error')
        return redirect(url_for('customers'))
        
    if not customer:
        flash('Customer not found.', 'error')
        return redirect(url_for('customers'))
        
    return render_template('edit_customer.html', customer=customer)

@app.route('/update/customer/<int:id>', methods=['POST'])
def update_customer(id):
    if not check_admin(): return redirect(url_for('login_page'))
    
    try:
        name = request.form['name']
        address = request.form['address']
        contact = request.form['contact']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        query = "UPDATE customers SET Name = %s, Address = %s, Contact = %s WHERE Customer_ID = %s"
        cursor.execute(query, (name, address, contact, id))
        conn.commit()
        cursor.close()
        conn.close()
        
        flash('Customer updated successfully!', 'success')
    except ms.Error as e:
        flash(f'Database error: {e.msg}', 'error')
    except Exception as e:
        flash(f'Error updating customer: {e}', 'error')
        
    return redirect(url_for('customers'))

@app.route('/edit/product/<int:id>', methods=['GET'])
def edit_product(id):
    if not check_admin(): return redirect(url_for('login_page'))
    
    conn = get_db_connection()
    if not conn:
        flash("Database connection error.")
        return redirect(url_for('products'))
        
    product = None
    manufacturers_list = []
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Get the specific product
        cursor.execute("SELECT * FROM products WHERE Product_ID = %s", (id,))
        product = cursor.fetchone()
        
        # Get all manufacturers for the dropdown
        cursor.execute("SELECT Manufacturer_ID, Name FROM manufacturers")
        manufacturers_list = cursor.fetchall()
        
        cursor.close()
        conn.close()
    except Exception as e:
        flash(f'Error fetching product data: {e}', 'error')
        return redirect(url_for('products'))
        
    if not product:
        flash('Product not found.', 'error')
        return redirect(url_for('products'))
        
    return render_template('edit_product.html', product=product, manufacturers=manufacturers_list)

@app.route('/update/product/<int:id>', methods=['POST'])
def update_product(id):
    if not check_admin(): return redirect(url_for('login_page'))
    
    try:
        name = request.form['name']
        description = request.form['description']
        sku = request.form['sku']
        manufacturer_id = request.form['manufacturer_id']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        query = """
            UPDATE products 
            SET Name = %s, Description = %s, SKU = %s, Manufacturer_ID = %s 
            WHERE Product_ID = %s
        """
        cursor.execute(query, (name, description, sku, manufacturer_id, id))
        conn.commit()
        cursor.close()
        conn.close()
        
        flash('Product updated successfully!', 'success')
    except ms.Error as e:
        flash(f'Database error: {e.msg}', 'error')
    except Exception as e:
        flash(f'Error updating product: {e}', 'error')
        
    return redirect(url_for('products'))

@app.route('/edit/supplier/<int:id>', methods=['GET'])
def edit_supplier(id):
    if not check_admin(): return redirect(url_for('login_page'))
    
    supplier = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM suppliers WHERE Supplier_ID = %s", (id,))
        supplier = cursor.fetchone()
        cursor.close()
        conn.close()
    except Exception as e:
        flash(f'Error fetching supplier data: {e}', 'error')
        return redirect(url_for('suppliers'))
        
    if not supplier:
        flash('Supplier not found.', 'error')
        return redirect(url_for('suppliers'))
        
    return render_template('edit_supplier.html', supplier=supplier)

@app.route('/update/supplier/<int:id>', methods=['POST'])
def update_supplier(id):
    if not check_admin(): return redirect(url_for('login_page'))
    
    try:
        name = request.form['name']
        address = request.form['address']
        contact = request.form['contact']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        query = "UPDATE suppliers SET Name = %s, Address = %s, Contact = %s WHERE Supplier_ID = %s"
        cursor.execute(query, (name, address, contact, id))
        conn.commit()
        cursor.close()
        conn.close()
        
        flash('Supplier updated successfully!', 'success')
    except ms.Error as e:
        flash(f'Database error: {e.msg}', 'error')
    except Exception as e:
        flash(f'Error updating supplier: {e}', 'error')
        
    return redirect(url_for('suppliers'))

@app.route('/edit/manufacturer/<int:id>', methods=['GET'])
def edit_manufacturer(id):
    if not check_admin(): return redirect(url_for('login_page'))
    
    manufacturer = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM manufacturers WHERE Manufacturer_ID = %s", (id,))
        manufacturer = cursor.fetchone()
        cursor.close()
        conn.close()
    except Exception as e:
        flash(f'Error fetching manufacturer data: {e}', 'error')
        return redirect(url_for('manufacturers'))
        
    if not manufacturer:
        flash('Manufacturer not found.', 'error')
        return redirect(url_for('manufacturers'))
        
    return render_template('edit_manufacturer.html', manufacturer=manufacturer)

@app.route('/update/manufacturer/<int:id>', methods=['POST'])
def update_manufacturer(id):
    if not check_admin(): return redirect(url_for('login_page'))
    
    try:
        name = request.form['name']
        address = request.form['address']
        contact = request.form['contact']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        query = "UPDATE manufacturers SET Name = %s, Address = %s, Contact = %s WHERE Manufacturer_ID = %s"
        cursor.execute(query, (name, address, contact, id))
        conn.commit()
        cursor.close()
        conn.close()
        
        flash('Manufacturer updated successfully!', 'success')
    except ms.Error as e:
        flash(f'Database error: {e.msg}', 'error')
    except Exception as e:
        flash(f'Error updating manufacturer: {e}', 'error')
        
    return redirect(url_for('manufacturers'))

@app.route('/edit/warehouse/<int:id>', methods=['GET'])
def edit_warehouse(id):
    if not check_admin(): return redirect(url_for('login_page'))
    
    warehouse = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM warehouses WHERE Warehouse_ID = %s", (id,))
        warehouse = cursor.fetchone()
        cursor.close()
        conn.close()
    except Exception as e:
        flash(f'Error fetching warehouse data: {e}', 'error')
        return redirect(url_for('warehouses'))
        
    if not warehouse:
        flash('Warehouse not found.', 'error')
        return redirect(url_for('warehouses'))
        
    return render_template('edit_warehouse.html', warehouse=warehouse)

@app.route('/update/warehouse/<int:id>', methods=['POST'])
def update_warehouse(id):
    if not check_admin(): return redirect(url_for('login_page'))
    
    try:
        name = request.form['name']
        location = request.form['location']
        capacity = request.form['capacity']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        query = "UPDATE warehouses SET Name = %s, Location = %s, Capacity = %s WHERE Warehouse_ID = %s"
        cursor.execute(query, (name, location, capacity, id))
        conn.commit()
        cursor.close()
        conn.close()
        
        flash('Warehouse updated successfully!', 'success')
    except ms.Error as e:
        flash(f'Database error: {e.msg}', 'error')
    except Exception as e:
        flash(f'Error updating warehouse: {e}', 'error')
        
    return redirect(url_for('warehouses'))

@app.route('/edit/vehicle/<int:id>', methods=['GET'])
def edit_vehicle(id):
    if not check_admin(): return redirect(url_for('login_page'))
    
    vehicle = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM vehicles WHERE Vehicle_ID = %s", (id,))
        vehicle = cursor.fetchone()
        cursor.close()
        conn.close()
    except Exception as e:
        flash(f'Error fetching vehicle data: {e}', 'error')
        return redirect(url_for('vehicles'))
        
    if not vehicle:
        flash('Vehicle not found.', 'error')
        return redirect(url_for('vehicles'))
        
    return render_template('edit_vehicle.html', vehicle=vehicle)

@app.route('/update/vehicle/<int:id>', methods=['POST'])
def update_vehicle(id):
    if not check_admin(): return redirect(url_for('login_page'))
    
    try:
        v_type = request.form['type']
        license_plate = request.form['license_plate']
        capacity = request.form['capacity']
        status = request.form['status']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        query = """
            UPDATE vehicles 
            SET Type = %s, License_Plate = %s, Capacity = %s, Status = %s
            WHERE Vehicle_ID = %s
        """
        cursor.execute(query, (v_type, license_plate, capacity, status, id))
        conn.commit()
        cursor.close()
        conn.close()
        
        flash('Vehicle updated successfully!', 'success')
    except ms.Error as e:
        flash(f'Database error: {e.msg}', 'error')
    except Exception as e:
        flash(f'Error updating vehicle: {e}', 'error')
        
    return redirect(url_for('vehicles'))

@app.route('/edit/order/<int:id>', methods=['GET'])
def edit_order(id):
    if not check_admin(): return redirect(url_for('login_page'))
    
    conn = get_db_connection()
    if not conn:
        flash("Database connection error.")
        return redirect(url_for('orders'))
        
    order = None
    customers_list = []
    try:
        cursor = conn.cursor(dictionary=True)
        
        # 1. Get the specific order
        cursor.execute("SELECT * FROM orders WHERE Order_ID = %s", (id,))
        order = cursor.fetchone()
        
        # 2. Get all customers for the dropdown
        cursor.execute("SELECT Customer_ID, Name FROM customers ORDER BY Name")
        customers_list = cursor.fetchall()
        
        cursor.close()
        conn.close()
    except Exception as e:
        flash(f'Error fetching order data: {e}', 'error')
        return redirect(url_for('orders'))
        
    if not order:
        flash('Order not found.', 'error')
        return redirect(url_for('orders'))
        
    if order['Date']:
        order['Date'] = order['Date'].strftime('%Y-%m-%d')
        
    return render_template('edit_order.html', order=order, customers=customers_list)

@app.route('/update/order/<int:id>', methods=['POST'])
def update_order(id):
    if not check_admin(): return redirect(url_for('login_page'))
    
    try:
        customer_id = request.form['customer_id']
        order_date = request.form['order_date']
        status = request.form['status']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        query = """
            UPDATE orders 
            SET Customer_ID = %s, Date = %s, Status = %s 
            WHERE Order_ID = %s
        """
        cursor.execute(query, (customer_id, order_date, status, id))
        conn.commit()
        cursor.close()
        conn.close()
        
        flash('Order updated successfully!', 'success')
    except ms.Error as e:
        flash(f'Database error: {e.msg}', 'error')
    except Exception as e:
        flash(f'Error updating order: {e}', 'error')
        
    return redirect(url_for('orders'))

# --------------------------------------------------------------------Report Routes-------------------------------------------------------------------------------
#                                                       ------------10 report routes------------
# ----------------------------------------------------------------------------------------------------------------------------------------------------------------

@app.route('/report/top_customers')
def report_top_customers():
    title = "Top 5 Customers by Purchase Value"
    query = """
        SELECT C.Name, SUM(I.Amount) AS TotalPurchaseValue
        FROM invoices I
        JOIN orders O ON I.Order_ID = O.Order_ID
        JOIN customers C ON O.Customer_ID = C.Customer_ID
        WHERE I.Status = 'Paid'
        GROUP BY C.Name
        ORDER BY TotalPurchaseValue DESC
        LIMIT 5
    """
    return run_report_query(title, query)

@app.route('/report/low_stock')
def report_low_stock():
    title = "Low-Stock Products (Stock < 100)"
    query = """
        SELECT W.Name AS Warehouse, P.Name AS Product, WI.Stock
        FROM warehouse_inventory WI
        JOIN products P ON WI.Product_ID = P.Product_ID
        JOIN warehouses W ON WI.Warehouse_ID = W.Warehouse_ID
        WHERE WI.Stock < 100
        ORDER BY WI.Stock ASC
    """
    return run_report_query(title, query)

@app.route('/report/delayed_shipments')
def report_delayed_shipments():
    title = "Delayed Shipments (En Route past Arrival Date)"
    query = """
        SELECT Shipment_ID, Order_ID, Destination, Arrival_Date
        FROM shipments
        WHERE Status = 'En Route' AND Arrival_Date < CURDATE()
        ORDER BY Arrival_Date ASC
    """
    return run_report_query(title, query)

@app.route('/report/revenue_by_warehouse')
def report_revenue_by_warehouse():
    title = "Total Paid Revenue by Warehouse (Origin)"
    query = """
        SELECT S.Origin, SUM(I.Amount) AS TotalRevenue
        FROM invoices I
        JOIN orders O ON I.Order_ID = O.Order_ID
        JOIN shipments S ON O.Order_ID = S.Order_ID
        WHERE I.Status = 'Paid'
        GROUP BY S.Origin
        ORDER BY TotalRevenue DESC
    """
    return run_report_query(title, query)

@app.route('/report/overdue_invoices')
def report_overdue_invoices():
    title = "Overdue Pending Invoices"
    query = """
        SELECT Invoice_ID, Order_ID, Amount, Due_Date
        FROM invoices
        WHERE Status = 'Pending' AND Due_Date < CURDATE()
        ORDER BY Due_Date ASC
    """
    return run_report_query(title, query)

@app.route('/report/product_suppliers')
def report_product_suppliers():
    title = "All Products and Their Suppliers"
    query = """
        SELECT P.Name AS Product_Name, S.Name AS Supplier_Name, S.Contact AS Supplier_Contact
        FROM products P
        LEFT JOIN manufacturers M ON P.Manufacturer_ID = M.Manufacturer_ID
        LEFT JOIN manufacturer_suppliers MS ON M.Manufacturer_ID = MS.Manufacturer_ID
        LEFT JOIN suppliers S ON MS.Supplier_ID = S.Supplier_ID
        ORDER BY Product_Name
    """
    return run_report_query(title, query)

@app.route('/report/vehicle_frequency')
def report_vehicle_frequency():
    title = "Vehicle Shipment Frequency"
    query = """
        SELECT V.Type, V.License_Plate, COUNT(S.Shipment_ID) AS ShipmentCount
        FROM shipments S
        JOIN vehicles V ON S.Vehicle_ID = V.Vehicle_ID
        GROUP BY V.Vehicle_ID, V.Type, V.License_Plate
        ORDER BY ShipmentCount DESC
    """
    return run_report_query(title, query)

@app.route('/report/popular_products')
def report_popular_products():
    title = "Most Popular Products (by Quantity Ordered)"
    query = """
        SELECT P.Name, SUM(OI.Quantity) AS TotalQuantity
        FROM order_items OI
        JOIN products P ON OI.Product_ID = P.Product_ID
        GROUP BY P.Name
        ORDER BY TotalQuantity DESC
        LIMIT 10
    """
    return run_report_query(title, query)

@app.route('/report/avg_ship_duration')
def report_avg_ship_duration():
    title = "Average Shipment Duration"
    query = """
        SELECT AVG(DATEDIFF(Arrival_Date, Departure_Date)) AS AvgDurationInDays
        FROM shipments
        WHERE Status != 'Pending' AND Arrival_Date IS NOT NULL AND Departure_Date IS NOT NULL
    """
    return run_report_query(title, query)

@app.route('/report/product_by_manufacturer')
def report_product_by_manufacturer():
    title = "Product Count by Manufacturer"
    query = """
        SELECT M.Name, COUNT(P.Product_ID) AS ProductCount
        FROM products P
        JOIN manufacturers M ON P.Manufacturer_ID = M.Manufacturer_ID
        GROUP BY M.Name
        ORDER BY ProductCount DESC
    """
    return run_report_query(title, query)


# --- Delete Routes ---

def check_admin():
    if 'logged_in' not in session or session.get('role') != 'admin':
        flash('You do not have permission to perform this action.')
        return False
    return True

@app.route('/delete/customer/<int:id>')
def delete_customer(id):
    if not check_admin():
        return redirect(url_for('login_page'))
    
    conn = get_db_connection()
    if not conn:
        flash("Database connection error.")
        return redirect(url_for('customers'))
        
    try:
        cursor = conn.cursor()
        conn.start_transaction()

        # 1. Find all orders associated with this customer
        cursor.execute("SELECT Order_ID FROM orders WHERE Customer_ID = %s", (id,))
        order_ids = [item[0] for item in cursor.fetchall()]
        
        if order_ids:
            order_placeholder = ','.join(['%s'] * len(order_ids))
            
            # 2. Find all shipments for these orders
            cursor.execute(f"SELECT Shipment_ID FROM shipments WHERE Order_ID IN ({order_placeholder})", tuple(order_ids))
            shipment_ids = [item[0] for item in cursor.fetchall()]

            if shipment_ids:
                # 3. Delete from shipment_items
                shipment_placeholder = ','.join(['%s'] * len(shipment_ids))
                cursor.execute(f"DELETE FROM shipment_items WHERE Shipment_ID IN ({shipment_placeholder})", tuple(shipment_ids))

            # 4. Delete from invoices
            cursor.execute(f"DELETE FROM invoices WHERE Order_ID IN ({order_placeholder})", tuple(order_ids))
            # 5. Delete from shipments
            cursor.execute(f"DELETE FROM shipments WHERE Order_ID IN ({order_placeholder})", tuple(order_ids))
            # 6. Delete from order_items
            cursor.execute(f"DELETE FROM order_items WHERE Order_ID IN ({order_placeholder})", tuple(order_ids))
            # 7. Delete from orders
            cursor.execute(f"DELETE FROM orders WHERE Order_ID IN ({order_placeholder})", tuple(order_ids))

        # 8. Finally, delete the customer
        cursor.execute("DELETE FROM customers WHERE Customer_ID = %s", (id,))
        
        conn.commit()
        flash('Customer and all their related orders/invoices/shipments deleted!', 'success')
        
    except ms.Error as e:
        conn.rollback()
        flash(f'Error deleting customer: {e.msg}.', 'error')
    finally:
        cursor.close()
        conn.close()
        
    return redirect(url_for('customers'))

@app.route('/delete/order/<int:id>')
def delete_order(id):
    if 'logged_in' not in session:
        flash('You do not have permission to perform this action.')
        return redirect(url_for('login_page'))
    
    conn = get_db_connection()
    if not conn:
        flash("Database connection error.")
        return redirect(url_for('orders'))
        
    try:
        cursor = conn.cursor()
        
        # --- Start Transaction ---
        conn.start_transaction()
        
        # 1. Delete from invoices
        cursor.execute("DELETE FROM invoices WHERE Order_ID = %s", (id,))
        
        # 2. Delete from shipments
        cursor.execute("SELECT Shipment_ID FROM shipments WHERE Order_ID = %s", (id,))
        shipment_ids = [item[0] for item in cursor.fetchall()]
        
        if shipment_ids:
            # Delete from shipment_items
            placeholder = ','.join(['%s'] * len(shipment_ids))
            cursor.execute(f"DELETE FROM shipment_items WHERE Shipment_ID IN ({placeholder})", tuple(shipment_ids))
            
            # Now delete from shipments
            cursor.execute("DELETE FROM shipments WHERE Order_ID = %s", (id,))
        
        # 3. Delete from order_items
        cursor.execute("DELETE FROM order_items WHERE Order_ID = %s", (id,))
        
        # 4. Finally, delete from orders
        cursor.execute("DELETE FROM orders WHERE Order_ID = %s", (id,))
        
        # --- Commit Transaction ---
        conn.commit()
        
        flash('Order and all related records deleted successfully!', 'success')
        
    except ms.Error as e:
        conn.rollback()
        flash(f'Error deleting order: {e.msg}.', 'error')
    except Exception as e:
        conn.rollback()
        flash(f'An unexpected error occurred: {e}', 'error')
    finally:
        cursor.close()
        conn.close()
        
    return redirect(url_for('orders'))

@app.route('/delete/product/<int:id>')
def delete_product(id):
    if not check_admin():
        return redirect(url_for('login_page'))
    
    conn = get_db_connection()
    if not conn:
        flash("Database connection error.")
        return redirect(url_for('products'))
        
    try:
        cursor = conn.cursor()
        conn.start_transaction()
        
        # 1. Delete from order_items
        cursor.execute("DELETE FROM order_items WHERE Product_ID = %s", (id,))
        # 2. Delete from shipment_items
        cursor.execute("DELETE FROM shipment_items WHERE Product_ID = %s", (id,))
        # 3. Delete from warehouse_inventory
        cursor.execute("DELETE FROM warehouse_inventory WHERE Product_ID = %s", (id,))
        # 4. Finally, delete the product
        cursor.execute("DELETE FROM products WHERE Product_ID = %s", (id,))
        
        conn.commit()
        flash('Product and all related records deleted!', 'success')
    except ms.Error as e:
        conn.rollback()
        flash(f'Error deleting product: {e.msg}.', 'error')
    finally:
        cursor.close()
        conn.close()
        
    return redirect(url_for('products'))

@app.route('/delete/supplier/<int:id>')
def delete_supplier(id):
    if not check_admin():
        return redirect(url_for('login_page'))
    
    conn = get_db_connection()
    if not conn:
        flash("Database connection error.")
        return redirect(url_for('suppliers'))
        
    try:
        cursor = conn.cursor()
        conn.start_transaction()
        
        # 1. Delete from manufacturer_suppliers
        cursor.execute("DELETE FROM manufacturer_suppliers WHERE Supplier_ID = %s", (id,))
        # 2. Finally, delete the supplier
        cursor.execute("DELETE FROM suppliers WHERE Supplier_ID = %s", (id,))
        
        conn.commit()
        flash('Supplier and all related records deleted!', 'success')
    except ms.Error as e:
        conn.rollback()
        flash(f'Error deleting supplier: {e.msg}.', 'error')
    finally:
        cursor.close()
        conn.close()
        
    return redirect(url_for('suppliers'))

@app.route('/delete/manufacturer/<int:id>')
def delete_manufacturer(id):
    if not check_admin():
        return redirect(url_for('login_page'))
    
    conn = get_db_connection()
    if not conn:
        flash("Database connection error.")
        return redirect(url_for('manufacturers'))
        
    try:
        cursor = conn.cursor()
        conn.start_transaction()
        
        # 1. Find all products associated with this manufacturer
        cursor.execute("SELECT Product_ID FROM products WHERE Manufacturer_ID = %s", (id,))
        product_ids = [item[0] for item in cursor.fetchall()]

        if product_ids:
            product_placeholder = ','.join(['%s'] * len(product_ids))
            
            # 2. Delete from order_items
            cursor.execute(f"DELETE FROM order_items WHERE Product_ID IN ({product_placeholder})", tuple(product_ids))
            # 3. Delete from shipment_items
            cursor.execute(f"DELETE FROM shipment_items WHERE Product_ID IN ({product_placeholder})", tuple(product_ids))
            # 4. Delete from warehouse_inventory
            cursor.execute(f"DELETE FROM warehouse_inventory WHERE Product_ID IN ({product_placeholder})", tuple(product_ids))
            # 5. Delete from products
            cursor.execute(f"DELETE FROM products WHERE Product_ID IN ({product_placeholder})", tuple(product_ids))

        # 6. Delete from manufacturer_suppliers
        cursor.execute("DELETE FROM manufacturer_suppliers WHERE Manufacturer_ID = %s", (id,))
        # 7. Finally, delete the manufacturer
        cursor.execute("DELETE FROM manufacturers WHERE Manufacturer_ID = %s", (id,))
        
        conn.commit()
        flash('Manufacturer and all related products/records deleted!', 'success')
        
    except ms.Error as e:
        conn.rollback()
        flash(f'Error deleting manufacturer: {e.msg}.', 'error')
    finally:
        cursor.close()
        conn.close()
        
    return redirect(url_for('manufacturers'))

@app.route('/delete/warehouse/<int:id>')
def delete_warehouse(id):
    if not check_admin():
        return redirect(url_for('login_page'))
    
    conn = get_db_connection()
    if not conn:
        flash("Database connection error.")
        return redirect(url_for('warehouses'))
        
    try:
        cursor = conn.cursor()
        conn.start_transaction()
        
        # 1. Delete from warehouse_inventory
        cursor.execute("DELETE FROM warehouse_inventory WHERE Warehouse_ID = %s", (id,))
        # 2. Finally, delete the warehouse
        cursor.execute("DELETE FROM warehouses WHERE Warehouse_ID = %s", (id,))
        
        conn.commit()
        flash('Warehouse and all related inventory records deleted!', 'success')
    except ms.Error as e:
        conn.rollback()
        flash(f'Error deleting warehouse: {e.msg}.', 'error')
    finally:
        cursor.close()
        conn.close()
        
    return redirect(url_for('warehouses'))

@app.route('/delete/vehicle/<int:id>')
def delete_vehicle(id):
    if not check_admin():
        return redirect(url_for('login_page'))
    
    conn = get_db_connection()
    if not conn:
        flash("Database connection error.")
        return redirect(url_for('vehicles'))
        
    try:
        cursor = conn.cursor()
        conn.start_transaction()
        
        # 1. Find all shipments associated with this vehicle
        cursor.execute("SELECT Shipment_ID FROM shipments WHERE Vehicle_ID = %s", (id,))
        shipment_ids = [item[0] for item in cursor.fetchall()]

        if shipment_ids:
            # 2. Delete from shipment_items
            placeholder = ','.join(['%s'] * len(shipment_ids))
            cursor.execute(f"DELETE FROM shipment_items WHERE Shipment_ID IN ({placeholder})", tuple(shipment_ids))
            
            # 3. Delete from shipments
            cursor.execute("DELETE FROM shipments WHERE Vehicle_ID = %s", (id,))

        # 4. Finally, delete the vehicle
        cursor.execute("DELETE FROM vehicles WHERE Vehicle_ID = %s", (id,))
        
        conn.commit()
        flash('Vehicle and all related shipment records deleted!', 'success')
    except ms.Error as e:
        conn.rollback()
        flash(f'Error deleting vehicle: {e.msg}.', 'error')
    finally:
        cursor.close()
        conn.close()
        
    return redirect(url_for('vehicles'))

@app.route('/delete/invoice/<int:id>')
def delete_invoice(id):
    if not check_admin(): return redirect(url_for('login_page'))
    
    conn = get_db_connection()
    if not conn:
        flash("Database connection error.")
        return redirect(url_for('invoices'))
        
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM invoices WHERE Invoice_ID = %s", (id,))
        conn.commit()
        flash('Invoice deleted successfully!', 'success')
    except ms.Error as e:
        conn.rollback()
        flash(f'Error deleting invoice: {e.msg}.', 'error')
    finally:
        cursor.close()
        conn.close()
        
    return redirect(url_for('invoices'))