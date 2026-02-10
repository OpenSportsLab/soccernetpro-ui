from PyQt6.QtWidgets import QWidget, QVBoxLayout, QStackedLayout

# 1. Import the generic skeleton
from ui.common.welcome_widget import WelcomeWidget
from ui.common.workspace import UnifiedTaskPanel

# 2. Import Classification components
from ui.classification.media_player import ClassificationMediaPlayer
from ui.classification.event_editor import ClassificationEventEditor

# 3. Import Localization components
from ui.localization.media_player import LocCenterPanel
from ui.localization.event_editor import LocRightPanel

# 4. [NEW] Import Description components
from ui.description.media_player import DescriptionMediaPlayer
from ui.description.event_editor import DescriptionEventEditor

from ui.dense_description.event_editor import DenseRightPanel

class MainWindowUI(QWidget):
    """
    The main container that switches between Welcome, Classification, Localization,
    and the new Description views.
    
    It uses a QStackedLayout to manage the different modes.
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
            center_widget=ClassificationMediaPlayer(),
            right_widget=ClassificationEventEditor(),
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

        # --- View 3: [NEW] Description Workspace ---
        # This panel uses the shared tree structure but loads the Description-specific
        # media player and event editor.
        self.description_ui = UnifiedTaskPanel(
            center_widget=DescriptionMediaPlayer(),
            right_widget=DescriptionEventEditor(),
            tree_title="Action / Inputs", # Adapted title for Description structure
            filter_items=["Show All", "Show Completed", "Show Incomplete"],
            clear_text="Clear All"
        )

        # --- View 4: Dense Description Workspace ---
        self.dense_description_ui = UnifiedTaskPanel(
            center_widget=LocCenterPanel(), # Reuse Localization's player + timeline
            right_widget=DenseRightPanel(), # Our new custom panel
            tree_title="Videos",
            filter_items=["Show All", "Show Annotated", "Not Annotated"],
            clear_text="Clear All"
        )
        
        # Add all views to the Stack
        self.stack_layout.addWidget(self.welcome_widget)      # Index 0
        self.stack_layout.addWidget(self.classification_ui)   # Index 1
        self.stack_layout.addWidget(self.localization_ui)     # Index 2
        self.stack_layout.addWidget(self.description_ui)      # Index 3 
        self.stack_layout.addWidget(self.dense_description_ui) # Index 4 [NEW]
        
        self.main_layout.addLayout(self.stack_layout)
        
        # Start at Welcome screen
        self.show_welcome_view()

    def show_welcome_view(self):
        """Switch to the Welcome Screen (Index 0)."""
        self.stack_layout.setCurrentIndex(0)

    def show_classification_view(self):
        """Switch to the Classification Workspace (Index 1)."""
        self.stack_layout.setCurrentIndex(1)

    def show_localization_view(self):
        """Switch to the Localization Workspace (Index 2)."""
        self.stack_layout.setCurrentIndex(2)

    def show_description_view(self):
        """[NEW] Switch to the Description Workspace (Index 3)."""
        self.stack_layout.setCurrentIndex(3)

    def show_dense_description_view(self):
        self.stack_layout.setCurrentIndex(4)