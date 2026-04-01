from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTabWidget,
    QGridLayout, QLabel, QScrollArea, QMenu, QInputDialog, QSizePolicy
)
from PyQt6.QtCore import pyqtSignal, Qt

# ==================== Custom Widgets ====================
class LabelButton(QPushButton):
    """
    Custom Label Button that supports Right-Click signal.
    Used for the grid of labels inside each Head page.
    """
    rightClicked = pyqtSignal()
    doubleClicked = pyqtSignal()

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(28)
        self.setStyleSheet("padding: 2px 10px;")
        self.setProperty("class", "spotting_label_btn")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self.rightClicked.emit()
        else:
            super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.doubleClicked.emit()
        else:
            super().mouseDoubleClickEvent(event)


class HeadSpottingPage(QWidget):
    """
    A single page (Head/Category) containing a grid of LabelButtons.
    This corresponds to the content of one tab.
    """
    labelClicked = pyqtSignal(str)       
    addLabelRequested = pyqtSignal()     
    renameLabelRequested = pyqtSignal(str) 
    deleteLabelRequested = pyqtSignal(str) 

    def __init__(self, head_name, labels, parent=None):
        super().__init__(parent)
        self.head_name = head_name
        self.labels = labels
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(5)

        # Time display
        self.time_label = QLabel("Current Time: 00:00.000")
        self.time_label.setProperty("class", "spotting_time_lbl")
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.time_label)
        
        # Scroll area for buttons
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.scroll.setProperty("class", "spotting_scroll_area")
        
        layout.addWidget(self.scroll)
        
        self._populate_grid()

    def update_time_display(self, text):
        self.time_label.setText(f"Current Time: {text}")

    def refresh_labels(self, new_labels):
        self.labels = new_labels
        self._populate_grid()

    def _populate_grid(self):
        old_widget = self.scroll.takeWidget()
        if old_widget:
            old_widget.deleteLater()
            
        self.grid_container = QWidget()
        self.grid_layout = QVBoxLayout(self.grid_container)
        self.grid_layout.setSpacing(6)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        max_width = 360 
        
        #(Bin Packing) 
        
        buttons_info = []
        for lbl in self.labels:
            display_text = lbl.replace('_', ' ')
            btn = LabelButton(display_text)
            btn.clicked.connect(lambda _, l=lbl: self.labelClicked.emit(l))
            btn.rightClicked.connect(lambda l=lbl: self._show_context_menu(l))
            btn.doubleClicked.connect(lambda l=lbl: self.renameLabelRequested.emit(l))
            
            btn.adjustSize()
            btn_w = btn.sizeHint().width()
            buttons_info.append((btn, btn_w))
            
        buttons_info.sort(key=lambda x: x[1], reverse=True)
        
        rows = [] 
        
        for btn, btn_w in buttons_info:
            placed = False
            for row in rows:
                if row['width'] + btn_w + 6 <= max_width: 
                    row['layout'].addWidget(btn)
                    row['width'] += btn_w + 6
                    placed = True
                    break 
            
            if not placed:
                new_layout = QHBoxLayout()
                new_layout.setSpacing(6)
                new_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
                self.grid_layout.addLayout(new_layout)
                
                new_layout.addWidget(btn)
                rows.append({'layout': new_layout, 'width': btn_w})

        add_btn = QPushButton("+ Add Label to Current Time")
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setMinimumHeight(28) 
        add_btn.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

        add_btn.setStyleSheet("""
            QPushButton {
                padding: 2px 10px; 
                color: #FFFFFF; 
                font-weight: bold; 
                background-color: #007BFF; 
                border: none; 
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #0056b3; 
            }
            QPushButton:pressed {
                background-color: #004085;
            }
        """)
                
        add_btn.clicked.connect(self.addLabelRequested.emit)
        add_btn.adjustSize()
        add_btn_w = add_btn.sizeHint().width()
        
        placed_add = False
        for row in rows:
            if row['width'] + add_btn_w + 6 <= max_width:
                row['layout'].addWidget(add_btn)
                row['width'] += add_btn_w + 6
                placed_add = True
                break
                
        if not placed_add:
            new_layout = QHBoxLayout()
            new_layout.setSpacing(6)
            new_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
            self.grid_layout.addLayout(new_layout)
            new_layout.addWidget(add_btn)
            
        self.scroll.setWidget(self.grid_container)

    def _show_context_menu(self, label):
        display_label = label.replace('_', ' ')
        menu = QMenu(self)
        rename_action = menu.addAction(f"Rename '{display_label}'")
        delete_action = menu.addAction(f"Delete '{display_label}'")
        
        action = menu.exec(self.cursor().pos())
        if action == rename_action:
            self.renameLabelRequested.emit(label)
        elif action == delete_action:
            self.deleteLabelRequested.emit(label)


class SpottingTabWidget(QTabWidget):
    """
    Tab Widget managing multiple HeadSpottingPages.
    Supports adding/removing heads via tab interactions.
    """
    headAdded = pyqtSignal(str)          
    headRenamed = pyqtSignal(str, str)   
    headDeleted = pyqtSignal(str)        
    headSelected = pyqtSignal(str)       
    spottingTriggered = pyqtSignal(str, str) 
    labelAddReq = pyqtSignal(str)            
    labelRenameReq = pyqtSignal(str, str)    
    labelDeleteReq = pyqtSignal(str, str)    

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTabBarAutoHide(False)
        self.setMovable(False)
        self.setTabsClosable(False) 
        self.setProperty("class", "spotting_tabs")
        
        self.tabBar().tabBarClicked.connect(self._on_tab_bar_clicked)
        
        self.currentChanged.connect(self._on_tab_changed)
        
        self.tabBar().setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tabBar().customContextMenuRequested.connect(self._show_tab_context_menu)
        
        self._ignore_change = False
        self._plus_tab_index = -1
        self._head_keys_map = []
        self._previous_index = -1

    def update_schema(self, label_definitions):
        """Rebuilds the tabs based on the new schema."""
        self._ignore_change = True
        self.clear()
        self._head_keys_map = []
        
        heads = sorted(label_definitions.keys())
        for head in heads:
            labels = label_definitions[head].get('labels', [])
            page = HeadSpottingPage(head, labels)
            
            # Forward signals from page to main controller
            page.labelClicked.connect(lambda l, h=head: self.spottingTriggered.emit(h, l))
            page.addLabelRequested.connect(lambda h=head: self.labelAddReq.emit(h))
            page.renameLabelRequested.connect(lambda l, h=head: self.labelRenameReq.emit(h, l))
            page.deleteLabelRequested.connect(lambda l, h=head: self.labelDeleteReq.emit(h, l))
            
            display_head = head.replace('_', ' ')
            self.addTab(page, display_head)
            self._head_keys_map.append(head) 
            
        # Add the "+" tab at the end
        self._plus_tab_index = self.addTab(QWidget(), "+")
        self._ignore_change = False

    def update_current_time(self, time_str):
        current_widget = self.currentWidget()
        if isinstance(current_widget, HeadSpottingPage):
            current_widget.update_time_display(time_str)

    def set_current_head(self, head_name):
        if head_name in self._head_keys_map:
            idx = self._head_keys_map.index(head_name)
            self.setCurrentIndex(idx)
            self._previous_index = idx

    def _on_tab_bar_clicked(self, index):
        """
        [NEW] Handles clicks on the tab bar. 
        Specifically catches clicks on the "+" tab to trigger add_head.
        """
        if index == self._plus_tab_index and index != -1:
            # If user clicked the plus tab, prompt for new head
            self._handle_add_head()

    def _on_tab_changed(self, index):
        """
        Handles navigation between valid Head tabs.
        Ignores the "+" tab (handled by clicked event).
        """
        if self._ignore_change: return

        # If we somehow navigated to the plus tab (e.g. keyboard), 
        # we can either trigger the add or just try to bounce back.
        # Since we handle triggering in `tabBarClicked`, we mostly just ignore logic here
        # or update the valid head selection.
        
        if index != self._plus_tab_index and index != -1:
            # Logic for valid head selection
            if 0 <= index < len(self._head_keys_map):
                real_head = self._head_keys_map[index]
                self.headSelected.emit(real_head)
                self._previous_index = index
        
        elif index == self._plus_tab_index:
            # If we landed on the plus tab (via keyboard/code), 
            # ideally we stay on the previous one to avoid showing an empty page,
            # but if it's the *only* tab, we can't switch away.
            pass

    def _handle_add_head(self):
        """Opens dialog to add a new category."""
        name, ok = QInputDialog.getText(self, "New Task Head", "Enter head name (e.g. 'player_action'):")
        if ok and name.strip():
            self.headAdded.emit(name.strip())

    def _show_tab_context_menu(self, pos):
        index = self.tabBar().tabAt(pos)
        if index == -1 or index == self._plus_tab_index: return
        
        if 0 <= index < len(self._head_keys_map):
            real_head_name = self._head_keys_map[index]
            display_head_name = self.tabText(index)
            
            menu = QMenu(self)
            rename_act = menu.addAction(f"Rename '{display_head_name}'")
            delete_act = menu.addAction(f"Delete '{display_head_name}'")
            
            action = menu.exec(self.mapToGlobal(pos))
            if action == rename_act:
                new_name, ok = QInputDialog.getText(self, "Rename Head", f"Rename '{real_head_name}' to:", text=real_head_name)
                if ok and new_name.strip() and new_name != real_head_name:
                    self.headRenamed.emit(real_head_name, new_name.strip())
            elif action == delete_act:
                self.headDeleted.emit(real_head_name)


class AnnotationManagementWidget(QWidget):
    """
    Wrapper for SpottingTabWidget with a title.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        title_label = QLabel("Create Annotation")
        title_label.setProperty("class", "panel_header_lbl")
        layout.addWidget(title_label)
        
        self.tabs = SpottingTabWidget()
        layout.addWidget(self.tabs)

    def update_schema(self, label_definitions):
        self.tabs.update_schema(label_definitions)