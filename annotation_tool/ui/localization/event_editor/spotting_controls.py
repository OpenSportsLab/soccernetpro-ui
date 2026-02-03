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
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(40)
        # Styling for the label buttons
        self.setStyleSheet("""
            QPushButton {
                background-color: #444; 
                color: white; 
                border: 1px solid #555;
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
                text-align: center;
                padding: 4px;
            }
            QPushButton:hover { background-color: #555; border-color: #777; }
            QPushButton:pressed { background-color: #0078D7; border-color: #0078D7; }
        """)

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
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)

        # Time display
        self.time_label = QLabel("Current Time: 00:00.000")
        self.time_label.setStyleSheet("color: #00BFFF; font-weight: bold; font-family: Menlo; font-size: 14px;")
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.time_label)

        # Scroll area for buttons
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        
        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setSpacing(8)
        self.grid_layout.setContentsMargins(0,0,0,0)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        scroll.setWidget(self.grid_container)
        layout.addWidget(scroll)
        
        self._populate_grid()

    def update_time_display(self, text):
        self.time_label.setText(f"Current Time: {text}")

    def refresh_labels(self, new_labels):
        self.labels = new_labels
        self._populate_grid()

    def _populate_grid(self):
        # Clear existing items
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        cols = 2 
        row, col = 0, 0
        
        # Add label buttons
        for lbl in self.labels:
            display_text = lbl.replace('_', ' ')
            btn = LabelButton(display_text)
            btn.clicked.connect(lambda _, l=lbl: self.labelClicked.emit(l))
            btn.rightClicked.connect(lambda l=lbl: self._show_context_menu(l))
            btn.doubleClicked.connect(lambda l=lbl: self.renameLabelRequested.emit(l))
            self.grid_layout.addWidget(btn, row, col)
            col += 1
            if col >= cols:
                col = 0
                row += 1

        # Add "Add Label" button at the bottom
        add_btn = QPushButton("Add new label at current time")
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setMinimumHeight(45) 
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078D7;
                color: white;
                border: 1px solid #005A9E;
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #1084E3; border-color: #2094F3; }
            QPushButton:pressed { background-color: #005A9E; }
        """)
        add_btn.clicked.connect(self.addLabelRequested.emit)
        
        if col != 0: 
            row += 1
        self.grid_layout.addWidget(add_btn, row, 0, 1, 2) 

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
        self.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #444; border-radius: 4px; background: #2E2E2E; }
            QTabBar::tab {
                background: #3A3A3A; color: #BBB; padding: 8px 12px;
                border-top-left-radius: 4px; border-top-right-radius: 4px;
                margin-right: 2px;
            }
            QTabBar::tab:selected { background: #2E2E2E; color: white; font-weight: bold; border-bottom: 2px solid #00BFFF; }
            QTabBar::tab:hover { background: #444; color: white; }
        """)
        
        # [MODIFIED] Use tabBarClicked for the "+" button logic.
        # This fixes the issue where clicking the "+" tab (when it's the only one) 
        # wouldn't trigger currentChanged because the index didn't change.
        self.tabBar().tabBarClicked.connect(self._on_tab_bar_clicked)
        
        # Keep currentChanged for normal navigation between existing heads
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
        title_label.setStyleSheet("font-weight: bold; color: #888; margin-bottom: 2px;")
        layout.addWidget(title_label)
        
        self.tabs = SpottingTabWidget()
        layout.addWidget(self.tabs)

    def update_schema(self, label_definitions):
        self.tabs.update_schema(label_definitions)