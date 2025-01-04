import tkinter as tk
from tkinter import ttk, messagebox, colorchooser
from database import add_category, add_app, get_category_id, fetch_apps_with_categories, fetch_categories, toggle_app_favorite, update_category_color

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
        
        # Create Treeview for categories
        self.categories_tree = ttk.Treeview(list_frame, columns=('name', 'color', 'preview'), show='headings')
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.categories_tree.yview)
        self.categories_tree.configure(yscrollcommand=scrollbar.set)
        
        # Define columns
        self.categories_tree.heading('name', text='Category Name')
        self.categories_tree.heading('color', text='Color Code')  # Keep the heading but hide the column
        self.categories_tree.heading('preview', text='Color')
        
        self.categories_tree.column('name', width=200)
        self.categories_tree.column('color', width=0, minwidth=0, stretch=False)  # Hide the column by setting width to 0
        self.categories_tree.column('preview', width=50, anchor='center')
        
        # Bind double-click to color picker
        self.categories_tree.bind('<Double-1>', self.pick_color)
        
        # Pack tree and scrollbar
        self.categories_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Add category frame
        add_frame = ttk.LabelFrame(parent, text="Add New Category", padding=10)
        add_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(add_frame, text="Name:").pack(side='left')
        self.category_entry = ttk.Entry(add_frame, width=20)
        self.category_entry.pack(side='left', padx=5)
        
        ttk.Button(add_frame, text="Add", 
                  command=self.add_new_category).pack(side='left', padx=5)

        # Add help text
        help_text = "Double-click a category to change its color"
        ttk.Label(parent, text=help_text, font=('Arial', 9, 'italic')).pack(pady=5)

        self.refresh_categories()

    def create_color_preview(self, color):
        """Create a colored rectangle for preview"""
        canvas = tk.Canvas(self.categories_tree, width=20, height=20, bg=color)
        return canvas

    def refresh_categories(self):
        for item in self.categories_tree.get_children():
            self.categories_tree.delete(item)
        
        categories = fetch_categories()
        for name, color in categories:
            item = self.categories_tree.insert('', 'end', values=(
                name, 
                color,
                '■'  # Use a colored square symbol
            ))
            # Only color the preview column
            self.categories_tree.tag_configure(f'preview_{color}', foreground=color)
            self.categories_tree.set(item, 'preview', '■')
            self.categories_tree.item(item, tags=(f'preview_{color}',))

    def refresh_apps(self):
        # Clear existing items
        for item in self.apps_tree.get_children():
            self.apps_tree.delete(item)
        
        # Fetch and insert apps
        apps = fetch_apps_with_categories()
        for app_name, is_favorite, category in apps:
            self.apps_tree.insert('', 'end', values=(
                '⭐' if is_favorite else '☆',
                app_name,
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

    def pick_color(self, event):
        item = self.categories_tree.selection()[0]
        category = self.categories_tree.item(item)['values'][0]
        current_color = self.categories_tree.item(item)['values'][1]
        
        color = colorchooser.askcolor(
            color=current_color,
            title=f"Pick color for {category}",
            parent=self.dialog
        )
        
        if color[1]:  # If color was selected
            update_category_color(category, color[1])
            self.refresh_categories()
            self.refresh_category_combo()  # Refresh combo box in apps tab 