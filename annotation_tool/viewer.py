import os
from PyQt6.QtWidgets import QMainWindow, QMessageBox
from PyQt6.QtCore import Qt, QDir, QTimer
from PyQt6.QtGui import QKeySequence, QShortcut, QColor, QIcon
from PyQt6.QtMultimedia import QMediaPlayer

from models import AppStateModel
from ui.classification.panels import MainWindowUI

from controllers.router import AppRouter
from controllers.history_manager import HistoryManager
from controllers.classification.annotation_manager import AnnotationManager
from controllers.classification.navigation_manager import NavigationManager
from controllers.localization.localization_manager import LocalizationManager

from utils import resource_path, create_checkmark_icon, natural_sort_key

class ActionClassifierApp(QMainWindow):
    
    FILTER_ALL = 0
    FILTER_DONE = 1
    FILTER_NOT_DONE = 2
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SoccerNet Pro Analysis Tool")
        self.setGeometry(100, 100, 1400, 900)
        
        # 1. Init MVC
        self.ui = MainWindowUI()
        self.setCentralWidget(self.ui)
        self.model = AppStateModel()
        
        # 2. Init Controllers
        self.router = AppRouter(self)
        
        self.history_manager = HistoryManager(self)
        self.annot_manager = AnnotationManager(self)
        self.nav_manager = NavigationManager(self)
        self.loc_manager = LocalizationManager(self)
        
        # 3. Local State
        bright_blue = QColor("#00BFFF")
        self.done_icon = create_checkmark_icon(bright_blue)
        self.empty_icon = QIcon()
        
        # 4. Setup
        self.connect_signals()
        self.apply_stylesheet("Night")
        self.ui.right_panel.manual_box.setEnabled(False)
        self.setup_dynamic_ui()
        
        self._setup_shortcuts()
        
        # Start at welcome screen
        self.ui.show_welcome_view()

    def connect_signals(self):
        # --- Welcome Screen ---
        self.ui.welcome_widget.import_btn.clicked.connect(self.router.import_annotations)
        self.ui.welcome_widget.create_btn.clicked.connect(self.router.create_new_project_flow)

        # --- Left Panel (Classification) ---
        cls_controls = self.ui.left_panel.project_controls
        cls_controls.createRequested.connect(self.router.create_new_project_flow)
        cls_controls.loadRequested.connect(self.router.import_annotations)
        cls_controls.addVideoRequested.connect(self.nav_manager.add_items_via_dialog)
        cls_controls.closeRequested.connect(self.router.close_project)
        cls_controls.saveRequested.connect(self.router.class_fm.save_json)
        cls_controls.exportRequested.connect(self.router.class_fm.export_json)

        self.ui.left_panel.clear_btn.clicked.connect(self._on_class_clear_clicked)
        self.ui.left_panel.request_remove_item.connect(self.nav_manager.remove_single_action_item)
        self.ui.left_panel.action_tree.currentItemChanged.connect(self.nav_manager.on_item_selected)
        self.ui.left_panel.filter_combo.currentIndexChanged.connect(self.nav_manager.apply_action_filter)
        
        # --- Undo/Redo Connections (Moved to Right Panel for Classification) ---
        self.ui.right_panel.undo_btn.clicked.connect(self.history_manager.perform_undo)
        self.ui.right_panel.redo_btn.clicked.connect(self.history_manager.perform_redo)
        
        self.ui.localization_ui.right_panel.undo_btn.clicked.connect(self.history_manager.perform_undo)
        self.ui.localization_ui.right_panel.redo_btn.clicked.connect(self.history_manager.perform_redo)
        
        # --- Center Panel (Classification) ---
        self.ui.center_panel.play_btn.clicked.connect(self.nav_manager.play_video)
        self.ui.center_panel.multi_view_btn.clicked.connect(self.nav_manager.show_all_views)
        self.ui.center_panel.prev_action.clicked.connect(self.nav_manager.nav_prev_action)
        self.ui.center_panel.prev_clip.clicked.connect(self.nav_manager.nav_prev_clip)
        self.ui.center_panel.next_clip.clicked.connect(self.nav_manager.nav_next_clip)
        self.ui.center_panel.next_action.clicked.connect(self.nav_manager.nav_next_action)
        
        # --- Right Panel (Classification) ---
        # [修改] 移除了 save_btn 和 export_btn 的信号连接
        
        self.ui.right_panel.confirm_btn.clicked.connect(self.annot_manager.save_manual_annotation)
        self.ui.right_panel.clear_sel_btn.clicked.connect(self.annot_manager.clear_current_manual_annotation)
        self.ui.right_panel.add_head_clicked.connect(self.annot_manager.handle_add_label_head)
        self.ui.right_panel.remove_head_clicked.connect(self.annot_manager.handle_remove_label_head)

        # --- Localization Connections ---
        loc_controls = self.ui.localization_ui.left_panel.project_controls
        loc_controls.createRequested.connect(self.router.create_new_project_flow)
        loc_controls.closeRequested.connect(self.router.close_project)
        
        self.loc_manager.setup_connections()

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+O"), self).activated.connect(self.router.import_annotations)
        QShortcut(QKeySequence("Ctrl+S"), self).activated.connect(self._dispatch_save)
        QShortcut(QKeySequence("Ctrl+Shift+S"), self).activated.connect(self._dispatch_export)
        QShortcut(QKeySequence("Ctrl+E"), self).activated.connect(lambda: self.show_temp_msg("Settings", "Settings dialog not implemented yet."))
        QShortcut(QKeySequence("Ctrl+D"), self).activated.connect(lambda: self.show_temp_msg("Downloader", "Dataset Downloader not implemented yet."))
        
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
        QShortcut(QKeySequence("S"), self).activated.connect(lambda: self.show_temp_msg("Info", "Select an event and Edit Time via Right-click."))

    def _is_loc_mode(self):
        return self.ui.stack_layout.currentWidget() == self.ui.localization_ui

    def _dispatch_save(self):
        if self._is_loc_mode():
            self.router.loc_fm.overwrite_json()
        else:
            self.router.class_fm.save_json()

    def _dispatch_export(self):
        if self._is_loc_mode():
            self.router.loc_fm.export_json()
        else:
            self.router.class_fm.export_json()

    def _dispatch_play_pause(self):
        if self._is_loc_mode():
            player = self.loc_manager.center_panel.media_preview.player
            if player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                player.pause()
            else:
                player.play()
        else:
            self.nav_manager.play_video()

    def _dispatch_seek(self, delta_ms):
        player = None
        if self._is_loc_mode():
            player = self.loc_manager.center_panel.media_preview.player
        else:
            player = self.ui.center_panel.single_view_widget.player
            
        if player:
            new_pos = max(0, player.position() + delta_ms)
            player.setPosition(new_pos)

    def _dispatch_add_annotation(self):
        if self._is_loc_mode():
            current_head = self.loc_manager.current_head
            if current_head:
                self.loc_manager._on_label_add_req(current_head)
            else:
                self.show_temp_msg("Warning", "No Head/Category selected.", icon=QMessageBox.Icon.Warning)
        else:
            self.annot_manager.save_manual_annotation()

    def _on_class_clear_clicked(self):
        if not self.model.json_loaded and not self.model.action_item_data: return
        msg = QMessageBox(self)
        msg.setWindowTitle("Clear Workspace")
        msg.setText("Clear workspace? Unsaved changes will be lost.")
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel)
        if msg.exec() == QMessageBox.StandardButton.Yes:
            self.router.class_fm._clear_workspace(full_reset=True)

    def apply_stylesheet(self, mode):
        qss = "style.qss" if mode == "Night" else "style_day.qss"
        try:
            with open(resource_path(os.path.join("style", qss)), "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())
        except Exception as e:
            print(f"Style error: {e}")

    def check_and_close_current_project(self):
        if self.model.json_loaded:
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
            if msg_box.clickedButton() == btn_yes: return True
            else: return False
        return True

    def closeEvent(self, event):
        is_loc_mode = (self.ui.stack_layout.currentWidget() == self.ui.localization_ui)
        if is_loc_mode:
            has_data = bool(self.model.localization_events)
        else:
            has_data = bool(self.model.manual_annotations)
            
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
            if is_loc_mode:
                if self.router.loc_fm.overwrite_json(): event.accept()
                else: event.ignore()
            else:
                if self.router.class_fm.save_json(): event.accept()
                else: event.ignore()
        elif msg.clickedButton() == discard_btn:
            event.accept()
        else:
            event.ignore()

    def update_save_export_button_state(self):
        is_loc_mode = (self.ui.stack_layout.currentWidget() == self.ui.localization_ui)
        
        if is_loc_mode:
            has_data = bool(self.model.localization_events)
        else:
            has_data = bool(self.model.manual_annotations)
            
        can_export = self.model.json_loaded and has_data
        can_save = can_export and (self.model.current_json_path is not None) and self.model.is_data_dirty
        
        # Unified Controls for both panels
        self.ui.left_panel.project_controls.btn_save.setEnabled(can_save)
        self.ui.left_panel.project_controls.btn_export.setEnabled(can_export)
        self.ui.localization_ui.left_panel.project_controls.btn_save.setEnabled(can_save)
        self.ui.localization_ui.left_panel.project_controls.btn_export.setEnabled(can_export)
        
        # Classification Right Panel buttons
        # self.ui.right_panel.export_btn.setEnabled(can_export)
        # self.ui.right_panel.save_btn.setEnabled(can_save)
        
        can_undo = len(self.model.undo_stack) > 0
        can_redo = len(self.model.redo_stack) > 0
        
        # Classification now uses Right Panel Undo/Redo
        self.ui.right_panel.undo_btn.setEnabled(can_undo)
        self.ui.right_panel.redo_btn.setEnabled(can_redo)
        
        # Localization Undo/Redo
        self.ui.localization_ui.right_panel.undo_btn.setEnabled(can_undo)
        self.ui.localization_ui.right_panel.redo_btn.setEnabled(can_redo)

    def show_temp_msg(self, title, msg, duration=1500, icon=QMessageBox.Icon.Information):
        m = QMessageBox(self); m.setWindowTitle(title); m.setText(msg); m.setIcon(icon)
        m.setStandardButtons(QMessageBox.StandardButton.NoButton)
        QTimer.singleShot(duration, m.accept)
        m.exec()

    def get_current_action_path(self):
        curr = self.ui.left_panel.action_tree.currentItem()
        if not curr: return None
        if curr.parent() is None: return curr.data(0, Qt.ItemDataRole.UserRole)
        return curr.parent().data(0, Qt.ItemDataRole.UserRole)

    def populate_action_tree(self):
        self.ui.left_panel.action_tree.clear()
        self.model.action_item_map.clear()
        
        sorted_list = sorted(self.model.action_item_data, key=lambda d: natural_sort_key(d.get('name', '')))
        for data in sorted_list:
            item = self.ui.left_panel.add_action_item(data['name'], data['path'], data.get('source_files'))
            self.model.action_item_map[data['path']] = item
            
        for path in self.model.action_item_map.keys():
            self.update_action_item_status(path)
        self.nav_manager.apply_action_filter()

        if self.ui.left_panel.action_tree.topLevelItemCount() > 0:
            first_item = self.ui.left_panel.action_tree.topLevelItem(0)
            self.ui.left_panel.action_tree.setCurrentItem(first_item)
            QTimer.singleShot(200, self.nav_manager.play_video)

    def update_action_item_status(self, action_path):
        item = self.model.action_item_map.get(action_path)
        if not item: return
        is_done = (action_path in self.model.manual_annotations and bool(self.model.manual_annotations[action_path]))
        item.setIcon(0, self.done_icon if is_done else self.empty_icon)
        self.nav_manager.apply_action_filter()

    def setup_dynamic_ui(self):
        self.ui.right_panel.setup_dynamic_labels(self.model.label_definitions)
        self.ui.right_panel.task_label.setText(f"Task: {self.model.current_task_name}")
        self._connect_dynamic_type_buttons()

    def _connect_dynamic_type_buttons(self):
        for head, group in self.ui.right_panel.label_groups.items():
            try: group.add_btn.clicked.disconnect()
            except: pass
            try: group.remove_label_signal.disconnect()
            except: pass
            try: group.value_changed.disconnect()
            except: pass
            
            group.add_btn.clicked.connect(lambda _, h=head: self.annot_manager.add_custom_type(h))
            group.remove_label_signal.connect(lambda lbl, h=head: self.annot_manager.remove_custom_type(h, lbl))
            group.value_changed.connect(lambda h, v: self.annot_manager.handle_ui_selection_change(h, v))

    def refresh_ui_after_undo_redo(self, action_path):
        if not action_path: return
        self.update_action_item_status(action_path)
        item = self.model.action_item_map.get(action_path)
        if item and self.ui.left_panel.action_tree.currentItem() != item:
            self.ui.left_panel.action_tree.setCurrentItem(item)
        
        current = self.get_current_action_path()
        if current == action_path: self.annot_manager.display_manual_annotation(action_path)
        self.update_save_export_button_state()