from PyQt6.QtWidgets import QWidget, QVBoxLayout, QStackedLayout

# 1. Import the generic skeleton
from ui.common.welcome_widget import WelcomeWidget
from ui.common.workspace import UnifiedTaskPanel

# 2. [FIX] Import Classification components from NEW folder structure
from ui.classification.media_player import ClassificationMediaPlayer
from ui.classification.event_editor import ClassificationEventEditor

# 3. Import Localization components
from ui.localization.media_player import LocCenterPanel
from ui.localization.event_editor import LocRightPanel

class MainWindowUI(QWidget):
    """
    The main container that switches between Welcome, Classification, and Localization views.
    Now composes views using UnifiedTaskPanel.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        self.stack_layout = QStackedLayout()
        
        # --- View 0: Welcome Screen ---
        self.welcome_widget = WelcomeWidget()
        
        # --- View 1: Classification Workspace ---
        self.classification_ui = UnifiedTaskPanel(
            center_widget=ClassificationMediaPlayer(), # [FIX] Use new class
            right_widget=ClassificationEventEditor(),  # [FIX] Use new class
            tree_title="Clips / Sequences",
            filter_items=["Show All", "Show Labelled", "No Labelled"], 
            clear_text="Clear All"
        )
        
        # --- View 2: Localization Workspace ---
        self.localization_ui = UnifiedTaskPanel(
            center_widget=LocCenterPanel(),
            right_widget=LocRightPanel(),
            tree_title="Clips / Sequences",
            filter_items=["Show All", "Show Labelled", "No Labelled"],
            clear_text="Clear All"
        )
        
        # Add to Stack
        self.stack_layout.addWidget(self.welcome_widget)      # Index 0
        self.stack_layout.addWidget(self.classification_ui)   # Index 1
        self.stack_layout.addWidget(self.localization_ui)     # Index 2
        
        self.main_layout.addLayout(self.stack_layout)
        self.show_welcome_view()

    def show_welcome_view(self):
        self.stack_layout.setCurrentIndex(0)

    def show_classification_view(self):
        self.stack_layout.setCurrentIndex(1)

    def show_localization_view(self):
        self.stack_layout.setCurrentIndex(2)