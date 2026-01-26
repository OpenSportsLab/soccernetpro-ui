import os

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QIcon, QKeySequence, QShortcut
from PyQt6.QtMultimedia import QMediaPlayer
from PyQt6.QtWidgets import QMainWindow, QMessageBox

from controllers.classification.annotation_manager import AnnotationManager
from controllers.classification.navigation_manager import NavigationManager
from controllers.history_manager import HistoryManager
from controllers.localization.localization_manager import LocalizationManager
from controllers.router import AppRouter
from models import AppStateModel

# [CHANGE] Import from the new common location
from ui.common.main_window import MainWindowUI
from utils import create_checkmark_icon, natural_sort_key, resource_path


class ActionClassifierApp(QMainWindow):
    """Main application window for annotation + localization workflows."""

    FILTER_ALL = 0
    FILTER_DONE = 1
    FILTER_NOT_DONE = 2

    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("SoccerNet Pro Analysis Tool")
        self.setGeometry(100, 100, 1400, 900)

        # --- MVC wiring ---
        self.ui = MainWindowUI()
        self.setCentralWidget(self.ui)
        self.model = AppStateModel()

        # --- Controllers ---
        self.router = AppRouter(self)
        self.history_manager = HistoryManager(self)
        self.annot_manager = AnnotationManager(self)
        self.nav_manager = NavigationManager(self)
        self.loc_manager = LocalizationManager(self)

        # --- Local UI state (icons, etc.) ---
        bright_blue = QColor("#00BFFF")
        self.done_icon = create_checkmark_icon(bright_blue)
        self.empty_icon = QIcon()

        # --- Setup ---
        self.connect_signals()
        self.load_stylesheet()
        
        # [CHANGE] Access classification UI via .classification_ui
        self.ui.classification_ui.right_panel.manual_box.setEnabled(False)
        
        self.setup_dynamic_ui()
        self._setup_shortcuts()

        # Start at welcome screen
        self.ui.show_welcome_view()

    # ---------------------------------------------------------------------
    # Wiring
    # ---------------------------------------------------------------------
    def connect_signals(self) -> None:
        """Connect UI signals to controller actions."""

        # Welcome screen
        self.ui.welcome_widget.import_btn.clicked.connect(self.router.import_annotations)
        self.ui.welcome_widget.create_btn.clicked.connect(self.router.create_new_project_flow)

        # [CHANGE] Classification - Left panel
        cls_left = self.ui.classification_ui.left_panel
        cls_controls = cls_left.project_controls
        
        cls_controls.createRequested.connect(self.router.create_new_project_flow)
        cls_controls.loadRequested.connect(self.router.import_annotations)
        cls_controls.addVideoRequested.connect(self.nav_manager.add_items_via_dialog)
        cls_controls.closeRequested.connect(self.router.close_project)
        cls_controls.saveRequested.connect(self.router.class_fm.save_json)
        cls_controls.exportRequested.connect(self.router.class_fm.export_json)

        cls_left.clear_btn.clicked.connect(self._on_class_clear_clicked)
        cls_left.request_remove_item.connect(self.nav_manager.remove_single_action_item)
        
        # [FIX] Changed 'action_tree' to 'tree' to match CommonProjectTreePanel
        cls_left.tree.currentItemChanged.connect(self.nav_manager.on_item_selected)
        cls_left.filter_combo.currentIndexChanged.connect(self.nav_manager.apply_action_filter)

        # [CHANGE] Classification - Center panel
        cls_center = self.ui.classification_ui.center_panel
        cls_center.play_btn.clicked.connect(self.nav_manager.play_video)
        cls_center.multi_view_btn.clicked.connect(self.nav_manager.show_all_views)
        cls_center.prev_action.clicked.connect(self.nav_manager.nav_prev_action)
        cls_center.prev_clip.clicked.connect(self.nav_manager.nav_prev_clip)
        cls_center.next_clip.clicked.connect(self.nav_manager.nav_next_clip)
        cls_center.next_action.clicked.connect(self.nav_manager.nav_next_action)

        # [CHANGE] Classification - Right panel
        cls_right = self.ui.classification_ui.right_panel
        cls_right.confirm_btn.clicked.connect(self.annot_manager.save_manual_annotation)
        cls_right.clear_sel_btn.clicked.connect(self.annot_manager.clear_current_manual_annotation)
        cls_right.add_head_clicked.connect(self.annot_manager.handle_add_label_head)
        cls_right.remove_head_clicked.connect(self.annot_manager.handle_remove_label_head)

        # Undo/redo (both panels share the same stacks)
        # [CHANGE] Use new paths for classification buttons
        cls_right.undo_btn.clicked.connect(self.history_manager.perform_undo)
        cls_right.redo_btn.clicked.connect(self.history_manager.perform_redo)
        
        # Localization Undo/Redo
        self.ui.localization_ui.right_panel.undo_btn.clicked.connect(self.history_manager.perform_undo)
        self.ui.localization_ui.right_panel.redo_btn.clicked.connect(self.history_manager.perform_redo)

        # Localization panel
        loc_controls = self.ui.localization_ui.left_panel.project_controls
        loc_controls.createRequested.connect(self.router.create_new_project_flow)
        loc_controls.closeRequested.connect(self.router.close_project)

        self.loc_manager.setup_connections()

    def _setup_shortcuts(self) -> None:
        """Register common keyboard shortcuts."""

        QShortcut(QKeySequence("Ctrl+O"), self).activated.connect(self.router.import_annotations)
        QShortcut(QKeySequence("Ctrl+S"), self).activated.connect(self._dispatch_save)
        QShortcut(QKeySequence("Ctrl+Shift+S"), self).activated.connect(self._dispatch_export)

        QShortcut(QKeySequence("Ctrl+E"), self).activated.connect(
            lambda: self.show_temp_msg("Settings", "Settings dialog not implemented yet.")
        )
        QShortcut(QKeySequence("Ctrl+D"), self).activated.connect(
            lambda: self.show_temp_msg("Downloader", "Dataset downloader not implemented yet.")
        )

        QShortcut(QKeySequence.StandardKey.Undo, self).activated.connect(self.history_manager.perform_undo)
        QShortcut(QKeySequence.StandardKey.Redo, self).activated.connect(self.history_manager.perform_redo)

        QShortcut(QKeySequence(Qt.Key.Key_Space), self).activated.connect(self._dispatch_play_pause)
        QShortcut(QKeySequence(Qt.Key.Key_Left), self).activated.connect(lambda: self._dispatch_seek(-40))
        QShortcut(QKeySequence(Qt.Key.Key_Right), self).activated.connect(lambda: self._dispatch_seek(40))
        QShortcut(QKeySequence("Ctrl+Left"), self).activated.connect(lambda: self._dispatch_seek(-1000))
        QShortcut(QKeySequence("Ctrl+Right"), self).activated.connect(lambda: self._dispatch_seek(1000))
        QShortcut(QKeySequence("Ctrl+Shift+Left"), self).activated.connect(lambda: self._dispatch_seek(-5000))
        QShortcut(QKeySequence("Ctrl+Shift+Right"), self).activated.connect(lambda: self._dispatch_seek(5000))

        QShortcut(QKeySequence("A"), self).activated.connect(self._dispatch_add_annotation)
        QShortcut(QKeySequence("S"), self).activated.connect(
            lambda: self.show_temp_msg("Info", "Select an event and edit time via right-click.")
        )

    # ---------------------------------------------------------------------
    # Mode-aware dispatchers
    # ---------------------------------------------------------------------
    def _is_loc_mode(self) -> bool:
        return self.ui.stack_layout.currentWidget() == self.ui.localization_ui

    def _dispatch_save(self) -> None:
        if self._is_loc_mode():
            self.router.loc_fm.overwrite_json()
        else:
            self.router.class_fm.save_json()

    def _dispatch_export(self) -> None:
        if self._is_loc_mode():
            self.router.loc_fm.export_json()
        else:
            self.router.class_fm.export_json()

    def _dispatch_play_pause(self) -> None:
        if self._is_loc_mode():
            player = self.loc_manager.center_panel.media_preview.player
            if player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                player.pause()
            else:
                player.play()
        else:
            self.nav_manager.play_video()

    def _dispatch_seek(self, delta_ms: int) -> None:
        """Seek the active player by delta_ms (milliseconds)."""
        if self._is_loc_mode():
            player = self.loc_manager.center_panel.media_preview.player
        else:
            # [CHANGE] Use classification_ui path
            player = self.ui.classification_ui.center_panel.single_view_widget.player

        if not player:
            return

        player.setPosition(max(0, player.position() + delta_ms))

    def _dispatch_add_annotation(self) -> None:
        """Add an annotation in the current mode."""
        if self._is_loc_mode():
            current_head = self.loc_manager.current_head
            if not current_head:
                self.show_temp_msg("Warning", "No head/category selected.", icon=QMessageBox.Icon.Warning)
                return
            self.loc_manager._on_label_add_req(current_head)
        else:
            self.annot_manager.save_manual_annotation()

    # ---------------------------------------------------------------------
    # UI actions / helpers
    # ---------------------------------------------------------------------
    def _on_class_clear_clicked(self) -> None:
        if not self.model.json_loaded and not self.model.action_item_data:
            return

        msg = QMessageBox(self)
        msg.setWindowTitle("Clear Workspace")
        msg.setText("Clear workspace? Unsaved changes will be lost.")
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel)

        if msg.exec() == QMessageBox.StandardButton.Yes:
            self.router.class_fm._clear_workspace(full_reset=True)

    def load_stylesheet(self) -> None:
        """Load the main (dark) theme stylesheet."""
        style_path = resource_path(os.path.join("style", "style.qss"))
        try:
            with open(style_path, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())
        except Exception as exc:
            print(f"Style error: {exc}")

    def check_and_close_current_project(self) -> bool:
        """Ask for confirmation if a project is open, especially with unsaved changes."""
        if not self.model.json_loaded:
            return True

        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Close Project")
        msg_box.setText("Opening a new project or closing will clear the current workspace. Continue?")
        msg_box.setIcon(QMessageBox.Icon.Warning)

        if self.model.is_data_dirty:
            msg_box.setInformativeText("You have unsaved changes in the current project.")

        btn_yes = msg_box.addButton("Yes", QMessageBox.ButtonRole.AcceptRole)
        btn_no = msg_box.addButton("No", QMessageBox.ButtonRole.RejectRole)
        msg_box.setDefaultButton(btn_no)
        msg_box.exec()

        return msg_box.clickedButton() == btn_yes

    def closeEvent(self, event) -> None:
        """Prompt to save if there are unsaved changes worth exporting."""
        is_loc_mode = self._is_loc_mode()
        has_data = bool(self.model.localization_events) if is_loc_mode else bool(self.model.manual_annotations)
        can_export = self.model.json_loaded and has_data

        if not self.model.is_data_dirty or not can_export:
            event.accept()
            return

        msg = QMessageBox(self)
        msg.setWindowTitle("Unsaved Annotations")
        msg.setText("Do you want to save your annotations before quitting?")
        msg.setIcon(QMessageBox.Icon.Question)

        save_btn = msg.addButton("Save & Exit", QMessageBox.ButtonRole.AcceptRole)
        discard_btn = msg.addButton("Discard & Exit", QMessageBox.ButtonRole.DestructiveRole)
        msg.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)

        msg.setDefaultButton(save_btn)
        msg.exec()

        if msg.clickedButton() == save_btn:
            ok = self.router.loc_fm.overwrite_json() if is_loc_mode else self.router.class_fm.save_json()
            event.accept() if ok else event.ignore()
        elif msg.clickedButton() == discard_btn:
            event.accept()
        else:
            event.ignore()

    def update_save_export_button_state(self) -> None:
        """Enable/disable save/export + undo/redo buttons based on current state."""
        is_loc_mode = self._is_loc_mode()
        has_data = bool(self.model.localization_events) if is_loc_mode else bool(self.model.manual_annotations)

        can_export = self.model.json_loaded and has_data
        can_save = can_export and (self.model.current_json_path is not None) and self.model.is_data_dirty

        # [CHANGE] Unified controls (Classification uses new path)
        self.ui.classification_ui.left_panel.project_controls.btn_save.setEnabled(can_save)
        self.ui.classification_ui.left_panel.project_controls.btn_export.setEnabled(can_export)
        
        # Localization uses existing path
        self.ui.localization_ui.left_panel.project_controls.btn_save.setEnabled(can_save)
        self.ui.localization_ui.left_panel.project_controls.btn_export.setEnabled(can_export)

        can_undo = len(self.model.undo_stack) > 0
        can_redo = len(self.model.redo_stack) > 0

        # [CHANGE] Classification panel buttons
        self.ui.classification_ui.right_panel.undo_btn.setEnabled(can_undo)
        self.ui.classification_ui.right_panel.redo_btn.setEnabled(can_redo)

        # Localization panel buttons
        self.ui.localization_ui.right_panel.undo_btn.setEnabled(can_undo)
        self.ui.localization_ui.right_panel.redo_btn.setEnabled(can_redo)

    def show_temp_msg(
        self,
        title: str,
        msg: str,
        duration: int = 1500,
        icon: QMessageBox.Icon = QMessageBox.Icon.Information,
    ) -> None:
        """Show a short-lived message box (auto-closes)."""
        box = QMessageBox(self)
        box.setWindowTitle(title)
        box.setText(msg)
        box.setIcon(icon)
        box.setStandardButtons(QMessageBox.StandardButton.NoButton)

        QTimer.singleShot(duration, box.accept)
        box.exec()

    def get_current_action_path(self):
        """Return the selected action path from the tree (top-level item path)."""
        # [CHANGE] Access tree via classification_ui
        curr = self.ui.classification_ui.left_panel.tree.currentItem()
        if not curr:
            return None

        if curr.parent() is None:
            return curr.data(0, Qt.ItemDataRole.UserRole)

        return curr.parent().data(0, Qt.ItemDataRole.UserRole)

    # [FIX] Renamed to populate_action_tree to match ClassFileManager calls
    def populate_action_tree(self) -> None:
        """Rebuild the action tree from model data and select the first item."""
        # [CHANGE] Access tree via classification_ui
        tree = self.ui.classification_ui.left_panel.tree
        tree.clear()
        self.model.action_item_map.clear()

        sorted_list = sorted(self.model.action_item_data, key=lambda d: natural_sort_key(d.get("name", "")))
        for data in sorted_list:
            # [CHANGE] Use helper method from left panel
            item = self.ui.classification_ui.left_panel.add_tree_item(data["name"], data["path"], data.get("source_files"))
            self.model.action_item_map[data["path"]] = item

        # Update completion icons once items exist
        for path in self.model.action_item_map.keys():
            self.update_action_item_status(path)

        self.nav_manager.apply_action_filter()

        if tree.topLevelItemCount() > 0:
            first_item = tree.topLevelItem(0)
            tree.setCurrentItem(first_item)
            QTimer.singleShot(200, self.nav_manager.play_video)

    def update_action_item_status(self, action_path: str) -> None:
        """Set the checkmark icon if an action has at least one manual annotation."""
        item = self.model.action_item_map.get(action_path)
        if not item:
            return

        is_done = action_path in self.model.manual_annotations and bool(self.model.manual_annotations[action_path])
        item.setIcon(0, self.done_icon if is_done else self.empty_icon)

        # Keep filter in sync as statuses change
        self.nav_manager.apply_action_filter()

    def setup_dynamic_ui(self) -> None:
        """Build right-panel label groups from the current task definition."""
        # [CHANGE] Access right panel via classification_ui
        cls_right = self.ui.classification_ui.right_panel
        cls_right.setup_dynamic_labels(self.model.label_definitions)
        cls_right.task_label.setText(f"Task: {self.model.current_task_name}")
        self._connect_dynamic_type_buttons()

    def _connect_dynamic_type_buttons(self) -> None:
        """Bind dynamic label widgets to the annotation manager."""
        # [CHANGE] Access label_groups via classification_ui
        for head, group in self.ui.classification_ui.right_panel.label_groups.items():
            # Avoid duplicate connections when rebuilding the UI
            try:
                group.add_btn.clicked.disconnect()
            except Exception:
                pass
            try:
                group.remove_label_signal.disconnect()
            except Exception:
                pass
            try:
                group.value_changed.disconnect()
            except Exception:
                pass

            group.add_btn.clicked.connect(lambda _, h=head: self.annot_manager.add_custom_type(h))
            group.remove_label_signal.connect(lambda lbl, h=head: self.annot_manager.remove_custom_type(h, lbl))
            group.value_changed.connect(lambda h, v: self.annot_manager.handle_ui_selection_change(h, v))

    def refresh_ui_after_undo_redo(self, action_path: str) -> None:
        """Refresh tree selection, status icons, and right panel after undo/redo."""
        if not action_path:
            return

        self.update_action_item_status(action_path)

        # [CHANGE] Access tree via classification_ui
        tree = self.ui.classification_ui.left_panel.tree
        item = self.model.action_item_map.get(action_path)
        
        if item and tree.currentItem() != item:
            tree.setCurrentItem(item)

        current = self.get_current_action_path()
        if current == action_path:
            self.annot_manager.display_manual_annotation(action_path)

        self.update_save_export_button_state()