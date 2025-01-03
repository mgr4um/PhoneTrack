import tkinter as tk
from tkinter import ttk, messagebox
from database import add_category, add_app, get_category_id, fetch_apps, fetch_categories, toggle_app_favorite

class SettingsDialog:
    def __init__(self, parent):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Settings")
        self.dialog.geometry("400x500")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Create notebook for tabs
        notebook = ttk.Notebook(self.dialog)
        notebook.pack(fill='both', expand=True, padx=10, pady=5)

        # Apps tab (first)
        apps_frame = ttk.Frame(notebook)
        notebook.add(apps_frame, text='Apps')
        self.setup_apps_tab(apps_frame)

        # Categories tab (second)
        categories_frame = ttk.Frame(notebook)
        notebook.add(categories_frame, text='Categories')
        self.setup_categories_tab(categories_frame)

    def setup_apps_tab(self, parent):
        # App list with favorite column
        list_frame = ttk.Frame(parent)
        list_frame.pack(fill='both', expand=True, pady=5)
        
        # Create Treeview with scrollbar
        self.apps_tree = ttk.Treeview(list_frame, columns=('favorite', 'name', 'category'), show='headings')
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.apps_tree.yview)
        self.apps_tree.configure(yscrollcommand=scrollbar.set)
        
        # Define columns
        self.apps_tree.heading('favorite', text='⭐')
        self.apps_tree.heading('name', text='App Name')
        self.apps_tree.heading('category', text='Category')
        
        self.apps_tree.column('favorite', width=30, anchor='center')
        self.apps_tree.column('name', width=150)
        self.apps_tree.column('category', width=100)
        
        # Bind double-click to toggle favorite
        self.apps_tree.bind('<Double-1>', self.toggle_favorite)
        
        # Pack tree and scrollbar
        self.apps_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Add app frame
        add_frame = ttk.LabelFrame(parent, text="Add New App", padding=10)
        add_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(add_frame, text="Name:").pack(side='left')
        self.app_entry = ttk.Entry(add_frame, width=20)
        self.app_entry.pack(side='left', padx=5)
        
        ttk.Label(add_frame, text="Category:").pack(side='left')
        self.category_var = tk.StringVar()
        self.category_combo = ttk.Combobox(add_frame, 
                                         textvariable=self.category_var,
                                         state='readonly',
                                         width=15)
        self.category_combo.pack(side='left', padx=5)
        self.refresh_category_combo()
        
        ttk.Button(add_frame, text="Add", 
                  command=self.add_new_app).pack(side='left', padx=5)
        
        self.refresh_apps()

    def setup_categories_tab(self, parent):
        # Category list with scrollbar
        list_frame = ttk.Frame(parent)
        list_frame.pack(fill='both', expand=True, pady=5)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side='right', fill='y')
        
        self.categories_list = tk.Listbox(list_frame, width=30, height=10,
                                        yscrollcommand=scrollbar.set)
        self.categories_list.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=self.categories_list.yview)
        
        self.refresh_categories()

        # Add category frame
        add_frame = ttk.LabelFrame(parent, text="Add New Category", padding=10)
        add_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(add_frame, text="Name:").pack(side='left')
        self.category_entry = ttk.Entry(add_frame, width=20)
        self.category_entry.pack(side='left', padx=5)
        
        ttk.Button(add_frame, text="Add", 
                  command=self.add_new_category).pack(side='left', padx=5)

    def refresh_categories(self):
        self.categories_list.delete(0, tk.END)
        for category in fetch_categories():
            self.categories_list.insert(tk.END, category)

    def refresh_apps(self):
        # Clear existing items
        for item in self.apps_tree.get_children():
            self.apps_tree.delete(item)
        
        # Fetch and insert apps
        apps = fetch_apps()
        for app, is_favorite, category in apps:
            self.apps_tree.insert('', 'end', values=(
                '⭐' if is_favorite else '☆',
                app,
                category
            ))

    def refresh_category_combo(self):
        self.category_combo['values'] = fetch_categories()

    def add_new_category(self):
        category_name = self.category_entry.get().strip()
        if category_name:
            add_category(category_name)
            self.category_entry.delete(0, tk.END)
            self.refresh_categories()
            self.refresh_category_combo()
        else:
            messagebox.showwarning("Warning", "Please enter a category name")

    def add_new_app(self):
        app_name = self.app_entry.get().strip()
        category = self.category_var.get()
        
        if app_name and category:
            category_id = get_category_id(category)
            if category_id:
                add_app(app_name, category_id)
                self.app_entry.delete(0, tk.END)
                self.refresh_apps()
            else:
                messagebox.showerror("Error", "Category not found")
        else:
            messagebox.showwarning("Warning", "Please enter app name and select category") 

    def toggle_favorite(self, event):
        """Toggle favorite status when double-clicking a row"""
        item = self.apps_tree.selection()[0]
        values = self.apps_tree.item(item)['values']
        if values:  # Make sure we have values
            app_name = values[1]  # App name is in second column
            toggle_app_favorite(app_name)
            # Update the star in the tree
            new_star = '☆' if values[0] == '⭐' else '⭐'
            self.apps_tree.set(item, 'favorite', new_star) 