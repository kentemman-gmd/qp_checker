import os
from qgis.core import QgsProject, QgsSettings
from qgis.PyQt.QtWidgets import QAction, QFileDialog, QDialog, QVBoxLayout, QPushButton, QLabel, QProgressBar
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
        qgs_button.clicked.connect(self.load_qgs_project)

        # Run button
        run_button = QPushButton("RUN")
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
            self.iface.messageBar().pushWarning("Error", "Please select a valid QML folder.")
            return

        # Check if the QGS file has been selected
        if not self.qgs_file:
            self.iface.messageBar().pushWarning("Error", "Please select a QGS project file.")
            return
        
        # Load the QGIS project
        try:
            QgsProject.instance().read(self.qgs_file)  # Load the QGIS project
        except Exception as e:
            self.iface.messageBar().pushCritical("Error", f"Failed to load QGS project: {e}")
            return

        # Proceed to rename layers and apply styles
        self.rename_layers()
        self.apply_styles_to_layers()

    def rename_layers(self):
        """Rename layers based on defined suffixes and check names in 'Base Layer' group."""
        suffixes_to_rename = {
            'bgy': '_bgy',
            'ea': '_ea',
            'bldg_point': '_bldg_point',
            'landmark': '_landmark',
            'river': '_river',
            'block': '_block',
        }

        # Get all layers in the project and convert to a list
        layers = list(QgsProject.instance().mapLayers().values())
        
        # Check layers in the "Base Layer" group
        base_layer_group = QgsProject.instance().layerTreeRoot().findGroup('Base Layer')
        if base_layer_group is not None:
            print("Checking layers in 'Base Layer' group:")
            for layer_tree_layer in base_layer_group.findLayers():
                layer_name = layer_tree_layer.name()
                print(f"Layer in 'Base Layer': {layer_name}")

        for idx, layer in enumerate(layers):
            layer_name = layer.name()
            renamed = False  # Flag to track if a renaming has occurred
            
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
            self.iface.messageBar().pushCritical("Error", "Group containing 'Form 8' not found.")
            return

        sf_layer_found = False
        gp_layer_found = False

        for layer_tree_layer in group.findLayers():
            layer_name = layer_tree_layer.name()
            if layer_name.endswith('_SF'):
                self.sf_layer = layer_tree_layer.layer()
                sf_layer_found = True
            elif layer_name.endswith('_GP'):
                self.gp_layer = layer_tree_layer.layer()
                gp_layer_found = True

        # Apply QML styles to the found layers
        if sf_layer_found and self.sf_layer.isValid() and os.path.exists(self.sf_qml_file):
            self.sf_layer.loadNamedStyle(self.sf_qml_file)
            self.sf_layer.triggerRepaint()
        else:
            self.iface.messageBar().pushCritical("Error", "SF layer not found or invalid.")

        if gp_layer_found and self.gp_layer.isValid() and os.path.exists(self.gp_qml_file):
            self.gp_layer.loadNamedStyle(self.gp_qml_file)
            self.gp_layer.triggerRepaint()
        else:
            self.iface.messageBar().pushCritical("Error", "GP layer not found or invalid.")

        # Update progress bar to 100% when finished
        self.progress_bar.setValue(100)
