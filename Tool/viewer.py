import os
from PyQt6.QtWidgets import QMainWindow, QMessageBox
from PyQt6.QtCore import Qt, QDir, QTimer
from PyQt6.QtGui import QKeySequence, QShortcut, QColor, QIcon

from models import AppStateModel
from ui.panels import MainWindowUI

# [修正] 导入路径调整
from controllers.router import AppRouter
from controllers.history_manager import HistoryManager  # <--- 去掉了 .common
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
        self._setup_shortcuts()
        self.apply_stylesheet("Night")
        self.ui.right_panel.manual_box.setEnabled(False)
        self.setup_dynamic_ui()
        
        # Start at welcome screen
        self.ui.show_welcome_view()

    def connect_signals(self):
        # --- Welcome Screen ---
        self.ui.welcome_widget.import_btn.clicked.connect(self.router.import_annotations)
        self.ui.welcome_widget.create_btn.clicked.connect(self.router.class_fm.create_new_project)

        # --- Left Panel (Classification File Ops) ---
        self.ui.left_panel.import_btn.clicked.connect(self.router.import_annotations)
        self.ui.left_panel.create_btn.clicked.connect(self.router.class_fm.create_new_project)
        self.ui.left_panel.clear_btn.clicked.connect(self._on_class_clear_clicked)
        
        # --- Left Panel (Classification Navigation) ---
        self.ui.left_panel.request_remove_item.connect(self.nav_manager.remove_single_action_item)
        self.ui.left_panel.action_tree.currentItemChanged.connect(self.nav_manager.on_item_selected)
        self.ui.left_panel.filter_combo.currentIndexChanged.connect(self.nav_manager.apply_action_filter)
        
        # --- Left Panel (Undo/Redo) ---
        self.ui.left_panel.undo_btn.clicked.connect(self.history_manager.perform_undo)
        self.ui.left_panel.redo_btn.clicked.connect(self.history_manager.perform_redo)
        
        # --- Center Panel (Classification Navigation) ---
        self.ui.center_panel.play_btn.clicked.connect(self.nav_manager.play_video)
        self.ui.center_panel.multi_view_btn.clicked.connect(self.nav_manager.show_all_views)
        self.ui.center_panel.prev_action.clicked.connect(self.nav_manager.nav_prev_action)
        self.ui.center_panel.prev_clip.clicked.connect(self.nav_manager.nav_prev_clip)
        self.ui.center_panel.next_clip.clicked.connect(self.nav_manager.nav_next_clip)
        self.ui.center_panel.next_action.clicked.connect(self.nav_manager.nav_next_action)
        
        # --- Right Panel (Classification File Ops) ---
        self.ui.right_panel.save_btn.clicked.connect(self.router.class_fm.save_json)
        self.ui.right_panel.export_btn.clicked.connect(self.router.class_fm.export_json)
        
        # --- Right Panel (Classification Annotation) ---
        self.ui.right_panel.confirm_btn.clicked.connect(self.annot_manager.save_manual_annotation)
        self.ui.right_panel.clear_sel_btn.clicked.connect(self.annot_manager.clear_current_manual_annotation)
        self.ui.right_panel.add_head_clicked.connect(self.annot_manager.handle_add_label_head)
        self.ui.right_panel.remove_head_clicked.connect(self.annot_manager.handle_remove_label_head)
        self.ui.right_panel.style_mode_changed.connect(self.apply_stylesheet)

        # --- Localization Connections ---
        self.loc_manager.setup_connections()

    def _on_class_clear_clicked(self):
        if not self.model.json_loaded and not self.model.action_item_data: return
        msg = QMessageBox(self)
        msg.setWindowTitle("Clear Workspace")
        msg.setText("Clear workspace? Unsaved changes will be lost.")
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel)
        if msg.exec() == QMessageBox.StandardButton.Yes:
            self.router.class_fm._clear_workspace(full_reset=True)

    def _setup_shortcuts(self):
        self.undo_shortcut = QShortcut(QKeySequence.StandardKey.Undo, self)
        self.undo_shortcut.activated.connect(self.history_manager.perform_undo)
        
        self.redo_shortcut = QShortcut(QKeySequence.StandardKey.Redo, self)
        self.redo_shortcut.activated.connect(self.history_manager.perform_redo)

    def apply_stylesheet(self, mode):
        qss = "style.qss" if mode == "Night" else "style_day.qss"
        try:
            with open(resource_path(os.path.join("style", qss)), "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())
        except Exception as e:
            print(f"Style error: {e}")

    # --- Shared Helpers ---
    
    def check_and_close_current_project(self):
        if self.model.json_loaded:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Open New Project")
            msg_box.setText("Opening a new project will clear the current workspace. Continue?")
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
        can_export = self.model.json_loaded and bool(self.model.manual_annotations)
        if not self.model.is_data_dirty or not can_export:
            event.accept(); return
        
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
            if self.ui.stack_layout.currentWidget() == self.ui.localization_ui:
                if self.router.loc_fm.save_json(): event.accept()
                else: event.ignore()
            else:
                if self.router.class_fm.save_json(): event.accept()
                else: event.ignore()
        elif msg.clickedButton() == discard_btn:
            event.accept()
        else:
            event.ignore()

    def update_save_export_button_state(self):
        can_export = self.model.json_loaded and bool(self.model.manual_annotations)
        can_save = can_export and (self.model.current_json_path is not None) and self.model.is_data_dirty
        self.ui.right_panel.export_btn.setEnabled(can_export)
        self.ui.right_panel.save_btn.setEnabled(can_save)
        self.ui.left_panel.undo_btn.setEnabled(len(self.model.undo_stack) > 0)
        self.ui.left_panel.redo_btn.setEnabled(len(self.model.redo_stack) > 0)

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
