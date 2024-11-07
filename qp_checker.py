import os
import shutil  # Make sure to import shutil at the top of your file
from qgis.core import QgsProject, QgsSettings, QgsLayerTreeLayer, QgsVectorDataProvider,QgsVectorLayer,QgsLayerTreeGroup
from qgis.PyQt.QtWidgets import QAction, QFileDialog, QDialog, QVBoxLayout, QPushButton, QLabel, QProgressBar, QMessageBox
from qgis.PyQt.QtGui import QIcon

class QPChecker:
    def __init__(self, iface):
        self.iface = iface  # Save reference to the QGIS interface
        self.action = None
        self.qml_folder = None
        self.sf_qml_file = None
        self.gp_qml_file = None
        self.sf_layer = None
        self.gp_layer = None
        self.plugin_dir = os.path.dirname(__file__)
        self.qgs_file = None  # Store the selected QGS file here
        self.settings = QgsSettings()  # Initialize settings to store paths

        # Load previously saved QML folder path if it exists
        self.qml_folder = self.settings.value("last_qml_folder", "")
        if self.qml_folder:
            self.sf_qml_file = os.path.join(self.qml_folder, "2. 2024 POPCEN-CBMS Form 8A.qml")
            self.gp_qml_file = os.path.join(self.qml_folder, "3. 2024 POPCEN-CBMS Form 8B.qml")

    def initGui(self):
        """Create the plugin menu item and toolbar icon."""
        icon_path = os.path.join(self.plugin_dir, 'icon.png')
        self.action = QAction(QIcon(icon_path), "QP Checker", self.iface.mainWindow())
        self.action.setShortcut("Ctrl+Shift+Z")  # Set a shortcut for opening the plugin
        self.action.triggered.connect(self.show_ui)
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu("&QP Checker", self.action)

    def unload(self):
        """Remove the plugin menu item and icon."""
        self.iface.removeToolBarIcon(self.action)
        self.iface.removePluginMenu("&QP Checker", self.action)

    def show_ui(self):
        """Show the plugin UI for selecting QML and QGS files."""        
        self.dialog = QDialog()
        self.dialog.setWindowTitle("QP Checker")
        self.dialog.setFixedWidth(300)  # Set the fixed width to 300 pixels
        layout = QVBoxLayout()

        # QML selection
        self.qml_label = QLabel("Select QML Folder: Not Selected" if not self.qml_folder else f"Select QML Folder: {self.qml_folder}")
        qml_button = QPushButton("Select QML")
        qml_button.clicked.connect(self.select_qml_folder)

        # QGS selection
        self.qgs_label = QLabel("Select QGS File: Not Selected")
        qgs_button = QPushButton("Select QGS")
        qgs_button.setShortcut("Ctrl+Shift+Z")  # Set a shortcut for selecting the QGS file
        qgs_button.clicked.connect(self.load_qgs_project)  # Connect to load QGS project

        # Run button
        run_button = QPushButton("Run")
        run_button.clicked.connect(self.run)

        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setMaximumHeight(20)  # Set the maximum height of the progress bar

        # Add widgets to layout
        layout.addWidget(self.qml_label)
        layout.addWidget(qml_button)
        layout.addWidget(self.qgs_label)
        layout.addWidget(qgs_button)
        layout.addWidget(run_button)
        layout.addWidget(self.progress_bar)  # Add progress bar to layout

        self.dialog.setLayout(layout)
        self.dialog.exec_()  # Show the dialog as modal

    def select_qml_folder(self):
        """Open a dialog to select a folder containing QML files."""
        folder_dialog = QFileDialog()
        self.qml_folder = folder_dialog.getExistingDirectory(None, "Select QML Folder")
        if self.qml_folder:
            self.sf_qml_file = os.path.join(self.qml_folder, "2. 2024 POPCEN-CBMS Form 8A.qml")
            self.gp_qml_file = os.path.join(self.qml_folder, "3. 2024 POPCEN-CBMS Form 8B.qml")
            self.qml_label.setText(f"Select QML Folder: {self.qml_folder}")  # Update label
            self.settings.setValue("last_qml_folder", self.qml_folder)  # Save the selected QML folder

    def load_qgs_project(self):
        """Open a dialog to select a QGS project file and store it."""        
        self.qgs_file = QFileDialog.getOpenFileName(None, "Select QGS Project", "", "QGS files (*.qgs *.qgz)")[0]
        if self.qgs_file:
            self.qgs_label.setText(f"QGS File: {self.qgs_file}")  # Update label
            

    def run(self):
        """Run the main logic when the RUN button is clicked."""
        # Check if the QML folder has been selected
        if not self.qml_folder:
            QMessageBox.warning(self.iface.mainWindow(), "Error", "Please select a valid QML folder.")
            return

        # Check if the QGS file has been selected
        if not self.qgs_file:
            QMessageBox.warning(self.iface.mainWindow(), "Error", "Please select a QGS project file.")
            return
        
        # Load the QGIS project
        try:
            QgsProject.instance().read(self.qgs_file)  # Load the QGIS project
        except Exception as e:
            QMessageBox.critical(self.iface.mainWindow(), "Error", f"Failed to load QGS project: {e}")
            return

        # Collapse base layer groups after loading the project
        

        # Proceed to rename layers, apply styles, and arrange layers
        self.rename_layers()
        self.rename_value_relation_layers()
        self.apply_styles_to_layers()
        self.arrange_base_layers()  # Call the function to arrange base layers
        self.update_layer_sources()
        QMessageBox.information(self.iface.mainWindow(), "Success", "QP Check completed successfully!")
        self.dialog.accept()  # Close the dialog

    def rename_layers(self):
        """Rename layers based on defined suffixes and check names in 'Base Layer' group."""
        suffixes_to_rename = {
            'bgy': 'bgy',
            'ea2024': 'ea',
            'ea': 'ea',
            'bldg': 'bldgpts',
            'bldg_points' : 'bldgpts',
            'landmark': 'landmark',
            'road': 'road',
            'road_updated': 'road',
            'updated_road' : 'road',
            'updated_river' : 'river',
            'river': 'river',
            'river_updated' : 'river',
            'block': 'block',
            'Block': 'block',
            'block2024': 'block',
        }

        # Get all layers in the project and convert to a list
        layers = list(QgsProject.instance().mapLayers().values())
        
        # Extract the 8-digit identifier from layers ending with '_SF' or '_SF.shp'
        eight_digit_id = None
        for layer in layers:
            if layer.name().endswith(('_SF', '_SF.shp')):  # Check for both endings
                eight_digit_id = layer.name()[:8]  # Extract the first 8 characters
                break  # Stop after finding the first matching layer

        # Check layers in the "Base Layer" group
        base_layer_group = None
        for variation in ['Base Layers', 'Base layers', 'Base Layer', 'Base layer', 'base layers']:
            base_layer_group = QgsProject.instance().layerTreeRoot().findGroup(variation)
            if base_layer_group is not None:
                break  # Stop searching after finding the first matching group

        if base_layer_group is not None:
            print("Checking layers in 'Base Layer' group:")
            for layer_tree_layer in base_layer_group.findLayers():
                layer_name = layer_tree_layer.name()
                print(f"Layer in 'Base Layer': {layer_name}")

                # Replace the 5-digit identifier with the 8-digit identifier only if it doesn't already have one
                if len(layer_name) >= 8 and not layer_name[:8].isdigit():  # Ensure the layer name is long enough and doesn't already start with 8 digits
                    new_name = eight_digit_id + layer_name[5:]  # Replace the first 5 digits
                    layer_tree_layer.layer().setName(new_name)
                    print(f"Renamed layer to: {new_name}")

        for idx, layer in enumerate(layers):
            layer_name = layer.name()
            renamed = False  # Flag to track if a renaming has occurred

             # Rename layers ending with '_SF.shp' to '_SF' if not already named '_SF'
            if layer_name.endswith('_SF.shp'):
                new_name = eight_digit_id + '_SF'  # Replace '_SF.shp' with '_SF'
                if not new_name in [layer.name() for layer in layers]:  # Check if the new name already exists
                    layer.setName(new_name)
                    output = f"Layer renamed to: {new_name}"
                    renamed = True
            
            # Rename layers ending with '_GP.shp' to '_GP' if not already named '_GP'
            elif layer_name.endswith('_GP.shp'):
                new_name = eight_digit_id + '_GP'  # Replace '_GP.shp' with '_GP'
                if not new_name in [layer.name() for layer in layers]:  # Check if the new name already exists
                    layer.setName(new_name)
                    output = f"Layer renamed to: {new_name}"
                    renamed = True
            
            for suffix, new_suffix in suffixes_to_rename.items():
                if suffix in layer_name and not layer_name.endswith(new_suffix):
                    # Rename the layer to the new suffix
                    new_name = layer_name.split(suffix)[0] + new_suffix
                    layer.setName(new_name)
                    output = f"Layer renamed to: {new_name}"
                    renamed = True
                    break  # Break after renaming for this layer
            
            if not renamed:
                output = f"No renaming needed for layer: {layer_name}"
            
            print(output)

            # Update progress bar
            self.progress_bar.setValue((idx + 1) * 100 // len(layers))

    

    def apply_styles_to_layers(self):
        """Find specific layers inside the group containing 'Form 8' and apply QML styles to them."""
        group = None
        
        # Iterate through all layer groups to find one containing 'Form 8' in its name
        for layer_group in QgsProject.instance().layerTreeRoot().children():
            if 'Form 8' in layer_group.name():
                group = layer_group
                break  # Stop searching after finding the first matching group

        if not group:
            QMessageBox.critical(self.iface.mainWindow(), "Error", "Group containing 'Form 8' not found.")
            return

        sf_layer_found = False
        gp_layer_found = False

        for layer_tree_layer in group.findLayers():
            layer_name = layer_tree_layer.name()
            if layer_name.endswith(('_SF', '_SF.shp')):
                self.sf_layer = layer_tree_layer.layer()
                sf_layer_found = True
            elif layer_name.endswith(('_GP', '_GP.shp')):
                self.gp_layer = layer_tree_layer.layer()
                gp_layer_found = True

        # Apply QML styles to the found layers
        if sf_layer_found and self.sf_layer.isValid() and os.path.exists(self.sf_qml_file):
            self.sf_layer.loadNamedStyle(self.sf_qml_file)
            self.sf_layer.triggerRepaint()
        else:
            QMessageBox.critical(self.iface.mainWindow(), "Error", "SF layer not found or invalid.")

        if gp_layer_found and self.gp_layer.isValid() and os.path.exists(self.gp_qml_file):
            self.gp_layer.loadNamedStyle(self.gp_qml_file)
            self.gp_layer.triggerRepaint()
        else:
            QMessageBox.critical(self.iface.mainWindow(), "Error", "GP layer not found or invalid.")

    # def arrange_base_layers(self):
    #     """Rearrange base layers in a specific order."""
    #     layer_order = ['river', 'road', 'block', 'ea', 'bgy', 'landmark', 'bldg_points']

    #     # Find the group containing base layers
    #     base_layer_group = QgsProject.instance().layerTreeRoot().findGroup('Base Layers')

    #     # Check if the group is valid
    #     if not base_layer_group:
    #         self.iface.messageBar().pushCritical("Error", "Base Layers group not found.")
    #         return

    #     # Get all layers in the group
    #     layers = [node.layer() for node in base_layer_group.children() if isinstance(node, QgsLayerTreeLayer)]
        
    #     # Log current layers in the group before rearrangement
    #     print("Current layers in the group before rearrangement:")
    #     for layer in layers:
    #         print(f"- {layer.name()}")

    #     self.rearrange_layers(base_layer_group, layers, layer_order)

    # def rearrange_layers(self, group, layers, layer_order):
    #     """Rearrange layers within the selected group according to the specified order."""
    #     # Create a mapping of layer names to their QgsLayerTreeLayer objects
    #     layer_dict = {layer.name(): layer for layer in layers}

    #     # Log the layers before rearrangement
    #     print("Current layers in the group before rearrangement:")
    #     for node in group.children():
    #         if isinstance(node, QgsLayerTreeLayer):
    #             print(f"- {node.layer().name()}")

    #     # Iterate over the desired layer order
    #     for layer_name in layer_order:
    #         matching_layer = next((layer for layer in layer_dict if layer_name in layer), None)

    #         if matching_layer:
    #             layer_to_duplicate = layer_dict[matching_layer]
    #             layer_tree_layer = QgsLayerTreeLayer(layer_to_duplicate)  # Duplicate the layer
    #             group.insertChildNode(0, layer_tree_layer)  # Insert it at the top
    #             print(f"Inserted duplicated layer '{layer_name}' into the group.")
    #         else:
    #             print(f"Layer '{layer_name}' not found in the layer dictionary.")

    #     # Log the layers after rearrangement
    #     print("Current layers in the group after rearrangement:")
    #     for node in group.children():
    #         if isinstance(node, QgsLayerTreeLayer):
    #             print(f"- {node.layer().name()}")

    #     # Call the method to remove duplicates after rearranging
    #     self.remove_duplicates(group)

    def arrange_base_layers(self):
        """Rearrange base layers in a specific order."""
        # Adjust 'bldg_points' to match various names like 'bldg_point', 'bldgps', 'bldgp', etc.
        layer_order = ['river', 'road', 'block', 'ea', 'bgy', 'landmark', 'bldg_point_variants']

        base_layer_group = None
        for variation in ['Base Layers', 'Base layers', 'Base Layer', 'Base layer', 'base layers']:
            base_layer_group = QgsProject.instance().layerTreeRoot().findGroup(variation)
            if base_layer_group is not None:
                break  #

        # Check if the group is valid
        if not base_layer_group:
            self.iface.messageBar().pushCritical("Error", "Base Layers group not found.")
            return

        # Get all layers in the group
        layers = [node.layer() for node in base_layer_group.children() if isinstance(node, QgsLayerTreeLayer)]
        
        # Log current layers in the group before rearrangement
        print("Current layers in the group before rearrangement:")
        for layer in layers:
            print(f"- {layer.name()}")

        self.rearrange_layers(base_layer_group, layers, layer_order)

    def rearrange_layers(self, group, layers, layer_order):
        """Rearrange layers within the selected group according to the specified order."""
        # Create a mapping of layer names to their QgsLayerTreeLayer objects
        layer_dict = {layer.name(): layer for layer in layers}

        # Iterate over the desired layer order
        for layer_name in layer_order:
            if layer_name == 'bldg_point_variants':
                # Handle bldg_point variations
                matching_layer = next((layer for layer in layer_dict if any(variant in layer for variant in ['bldg_point','bldg_points', 'bldgps', 'bldgp', 'bldgpts', 'bldgpt'])), None)
            else:
                matching_layer = next((layer for layer in layer_dict if layer_name in layer), None)

            if matching_layer:
                layer_to_duplicate = layer_dict[matching_layer]
                layer_tree_layer = QgsLayerTreeLayer(layer_to_duplicate)  # Duplicate the layer
                group.insertChildNode(0, layer_tree_layer)  # Insert it at the top
                print(f"Inserted duplicated layer '{layer_name}' into the group.")
            else:
                print(f"Layer '{layer_name}' not found in the layer dictionary.")

        # Call the method to remove duplicates after rearranging
        self.remove_duplicates(group)


    def remove_duplicates(self, group):
        """Remove duplicate layers from the given group."""
        layer_names = set()
        nodes_to_remove = []
        
        for node in group.children():
            if isinstance(node, QgsLayerTreeLayer):
                layer = node.layer()
                layer_name = layer.name()
                if layer_name in layer_names:
                    nodes_to_remove.append(node)
                    print(f"Removed duplicate layer: {layer.name()}")
                else:
                    layer_names.add(layer_name)
        
        for node in nodes_to_remove:
            group.removeChildNode(node)



    def update_layer_sources(self):
        """Update the data source for specific layers in the 'Value Relation' group in the QGIS project using the QML path and overwrite with new CSV files."""
        # Ensure the QML folder is set
        if not self.qml_folder:
            self.iface.messageBar().pushWarning("Error", "QML folder not selected.")
            return

        # Define the source paths for the CSV files using the QML folder
        source_sf_data_source = os.path.join(self.qml_folder, "2024_POPCEN-CBMS_SF_Specific_Types.csv")  # Use QML folder path
        source_gp_data_source = os.path.join(self.qml_folder, "2024_POPCEN-CBMS_GP_Fund.csv")  # Use QML folder path

        # Define the destination paths for the copied CSV files in the QGIS project directory
        project_dir = os.path.dirname(self.qgs_file)  # Get the directory of the QGS file
        dest_sf_data_source = os.path.join(project_dir, "2024 POPCEN-CBMS SF Specific Types.csv")
        dest_gp_data_source = os.path.join(project_dir, "2024 POPCEN-CBMS GP Fund.csv")

        # Copy the CSV files to the QGIS project directory
        try:
            shutil.copy(source_sf_data_source, dest_sf_data_source)  # Copy SF CSV
            print(f"Copied {source_sf_data_source} to {dest_sf_data_source}")
        except Exception as e:
            QMessageBox.warning(self.iface.mainWindow(), "Error", f"Failed to copy SF CSV: {e}")
            return

        try:
            shutil.copy(source_gp_data_source, dest_gp_data_source)  # Copy GP CSV
            print(f"Copied {source_gp_data_source} to {dest_gp_data_source}")
        except Exception as e:
            QMessageBox.warning(self.iface.mainWindow(), "Error", f"Failed to copy GP CSV: {e}")
            return

        # Find the "Value Relation" group
        value_relation_group = None
        for variation in ["Value Relation", "Value Relations", "Value Relations "]:  # Check for trailing space
            value_relation_group = QgsProject.instance().layerTreeRoot().findGroup(variation)
            if value_relation_group is not None:
                break  # Stop searching after finding the first matching group

        if value_relation_group is None:
            QMessageBox.warning(self.iface.mainWindow(), "Warning", "Value Relations group not found or has a trailing space.")
            return  # Exit if the group is not found

        # Update existing layers instead of removing them
        sf_layer_names = ["2024 POPCEN-CBMS SF Specific Types", "2024 POPCEN-CBMS_SF_Specific_Types","2024 POPCEN-CBMS SF Specific Types ","2024-POPCEN-CBMS-SF-Specific-Types","2024_POPCEN_CBMS_SF_Specific_Types","2024 POPCEN_CBMS_SF_Specific_Types", "2024_POPCEN-CBMS_SF_Specific_Types"]
        gp_layer_names = ["2024 POPCEN-CBMS GP Fund ", "2024 POPCEN-CBMS_GP_Fund", "2024 POPCEN-CBMS GP Fund", "2024-POPCEN-CBMS-GP-Fund", "2024_POPCEN_CBMS_GP_Fund", "2024 POPCEN_CBMS_GP_Fund", "2024_POPCEN-CBMS_GP_Fund"]

        for layer_tree_layer in value_relation_group.findLayers():
            layer = layer_tree_layer.layer()
            if layer.name() in sf_layer_names:
                # Validate if the layer exists before updating
                if layer.isValid() and os.path.exists(dest_sf_data_source):
                    # Update the data source for the SF layer
                    layer.setDataSource(dest_sf_data_source, layer.name(), "ogr")  # Update the data source
                    print(f"Updated SF data source for layer: {layer.name()} with {dest_sf_data_source}")
                else:
                    print(f"SF layer '{layer.name()}' is invalid or data source does not exist.")

            elif layer.name() in gp_layer_names:
                # Validate if the layer exists before updating
                if layer.isValid() and os.path.exists(dest_gp_data_source):
                    # Update the data source for the GP layer
                    layer.setDataSource(dest_gp_data_source, layer.name(), "ogr")  # Update the data source
                    print(f"Updated GP data source for layer: {layer.name()} with {dest_gp_data_source}")
                else:
                    print(f"GP layer '{layer.name()}' is invalid or data source does not exist.")


    def rename_value_relation_layers(self):
        """Rename layers in the 'Value Relation' group to standard names."""

        # Define the standard names and the list of alternative names to be checked
        standard_sf_name = "2024 POPCEN-CBMS SF Specific Types"
        standard_gp_name = "2024 POPCEN-CBMS GP Fund"
        
        sf_layer_names = [
            "2024 POPCEN-CBMS SF Specific Types", "2024 POPCEN-CBMS_SF_Specific_Types",
            "2024 POPCEN-CBMS SF Specific Types ", "2024-POPCEN-CBMS-SF-Specific-Types",
            "2024_POPCEN_CBMS_SF_Specific_Types", "2024 POPCEN_CBMS_SF_Specific_Types",
            "2024_POPCEN-CBMS_SF_Specific_Types"
        ]
        
        gp_layer_names = [
            "2024 POPCEN-CBMS GP Fund ", "2024 POPCEN-CBMS_GP_Fund",
            "2024 POPCEN-CBMS GP Fund", "2024-POPCEN-CBMS-GP-Fund",
            "2024_POPCEN_CBMS_GP_Fund", "2024 POPCEN_CBMS_GP_Fund",
            "2024_POPCEN-CBMS_GP_Fund"
        ]

        # Find the "Value Relation" group
        value_relation_group = None
        for variation in ["Value Relation", "Value Relations", "Value Relations "]:  # Check for trailing space
            value_relation_group = QgsProject.instance().layerTreeRoot().findGroup(variation)
            if value_relation_group is not None:
                break  # Stop searching after finding the first matching group

        if value_relation_group is None:
            QMessageBox.warning(self.iface.mainWindow(), "Warning", "Value Relations group not found or has a trailing space.")
            return  # Exit if the group is not found

        # Rename layers in the "Value Relation" group if they match any of the alternative names
        for layer_tree_layer in value_relation_group.findLayers():
            layer_name = layer_tree_layer.name()
            
            # Check if the layer name matches any alternative SF name and rename it to the standard SF name
            if layer_name in sf_layer_names:
                layer_tree_layer.layer().setName(standard_sf_name)
                print(f"Renamed layer '{layer_name}' to '{standard_sf_name}'")

            # Check if the layer name matches any alternative GP name and rename it to the standard GP name
            elif layer_name in gp_layer_names:
                layer_tree_layer.layer().setName(standard_gp_name)
                print(f"Renamed layer '{layer_name}' to '{standard_gp_name}'")

            else:
                print(f"No renaming needed for layer: {layer_name}")






     



