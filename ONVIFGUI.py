import sys

from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QPainter, QPixmap
from PyQt5.QtWidgets import QApplication, QWidget, QDialog, QLabel, \
   QDialogButtonBox, QVBoxLayout, QGroupBox, QFormLayout, QLineEdit, \
   QPushButton, QHBoxLayout, QGridLayout, QSlider
import onvif
from tinydb import TinyDB
from os import path


JOYSTICK_BUTTONS = [
   ['upleft', 'up', 'upright'],
   ['left', 'stop', 'right'],
   ['downleft', 'down', 'downright'],
   ['zoom+', 'zoom-'],
   ['focus+', 'focus-']
]
JOYSTICK_ICONS = {
   'upleft': '↖',
   'up': '↑',
   'upright': '↗',
   'left': '←',
   'stop': '⏹',
   'right': '→',
   'downleft': '↙',
   'down': '↓',
   'downright': '↘'
}

if getattr(sys, 'frozen', False):
   executable_path = f'{path.dirname(sys.executable)}/'
else:
   executable_path = ''
print(executable_path)
db = TinyDB(f'{executable_path}db.json')
cameras_table = db.table('cameras')
cameras = []


def setup_cameras():
   global cameras
   cameras = []
   for camera_number, camera in enumerate(cameras_table.all()):
      try:
         camera_kwargs = {}
         if getattr(sys, 'frozen', False):
            camera_kwargs['wsdl_dir'] =  f'{executable_path}wsdl'
         camera_obj = onvif.ONVIFCamera(
            camera['ip'],
            camera['port'],
            camera['user_name'],
            camera['password'],
            **camera_kwargs
         )
         camera_obj.name = camera['name']
         camera_obj.camera_number = camera_number
         camera_obj.create_media_service()
         camera_obj.media_profile = camera_obj.media.GetProfiles()[0]
         request = camera_obj.media.create_type('GetStreamUri')
         request.ProfileToken = camera_obj.media_profile.token
         request.StreamSetup = {
            'Stream': 'RTP-Unicast',
            'Transport': {
               'Protocol': 'HTTP'
            }
         }
         camera_obj.stream = camera_obj.media.GetStreamUri(request)

         camera_obj.create_ptz_service()
         camera_obj.presets = camera_obj.ptz.GetPresets({
            'ProfileToken': camera_obj.media_profile.token
         })
         camera_obj.ptz_config_options = camera_obj.ptz.GetConfigurationOptions({
            'ConfigurationToken': camera_obj.media_profile.PTZConfiguration.token
         })
         camera_obj.XMAX = camera_obj.ptz_config_options.Spaces.ContinuousPanTiltVelocitySpace[0].XRange.Max
         camera_obj.XMIN = camera_obj.ptz_config_options.Spaces.ContinuousPanTiltVelocitySpace[0].XRange.Min
         camera_obj.YMAX = camera_obj.ptz_config_options.Spaces.ContinuousPanTiltVelocitySpace[0].YRange.Max
         camera_obj.YMIN = camera_obj.ptz_config_options.Spaces.ContinuousPanTiltVelocitySpace[0].YRange.Min
         camera_obj.ZMAX = camera_obj.ptz_config_options.Spaces.ContinuousZoomVelocitySpace[0].XRange.Max
         camera_obj.ZMIN = camera_obj.ptz_config_options.Spaces.ContinuousZoomVelocitySpace[0].XRange.Min
         camera_obj.PTSPEED_MIN = camera_obj.ptz_config_options.Spaces.PanTiltSpeedSpace[0].XRange.Min
         camera_obj.PTSPEED_MAX = camera_obj.ptz_config_options.Spaces.PanTiltSpeedSpace[0].XRange.Max
         camera_obj.PTSPEED_RANGE = camera_obj.PTSPEED_MAX - camera_obj.PTSPEED_MIN
         camera_obj.ZSPEED_MIN = camera_obj.ptz_config_options.Spaces.ZoomSpeedSpace[0].XRange.Min
         camera_obj.ZSPEED_MAX = camera_obj.ptz_config_options.Spaces.ZoomSpeedSpace[0].XRange.Max
         camera_obj.ZSPEED_RANGE = camera_obj.ZSPEED_MAX - camera_obj.ZSPEED_MIN

         camera_obj.video_source_token = camera_obj.media_profile.VideoSourceConfiguration.SourceToken
         camera_obj.create_imaging_service()
         camera_obj.move_options = camera_obj.imaging.GetMoveOptions({
            'VideoSourceToken': camera_obj.video_source_token
         })
         camera_obj.FMIN = camera_obj.move_options.Continuous.Speed.Min
         camera_obj.FMAX = camera_obj.move_options.Continuous.Speed.Max

         cameras.append(camera_obj)
      except onvif.exceptions.ONVIFError as e:
         print(type(e), e)
         pass
   return cameras
cameras = setup_cameras()


def get_cameras():
   global cameras
   return cameras


def setup_cameras_window():
   window = QWidget()
   window.setWindowTitle('Set Up Cameras')
   return window


class ImageButton(QPushButton):
   def __init__(self, path, parent=None, width=None):
      super().__init__(parent)
      self.path = path
      self.pixmap = QPixmap(self.path)
      self.width = width

   def paintEvent(self, event):
      painter = QPainter(self)
      painter.drawPixmap(event.rect(), self.pixmap)

   def heightForWidth(self, w):
      return int(w / 1.78)

   def hasHeightForWidth(self):
      return True

   def sizeHint(self):
      return QSize(275, 154)

   def refresh(self, path=None):
      self.pixmap = QPixmap(path)
      self.repaint()


class MainWindow(QWidget):
    def __init__(self, *args, **kwargs):
       super().__init__(*args, **kwargs)
       self.setWindowTitle('Camera Controller')

       if not get_cameras():
          open_camera_dialog()

       self.setup_layout()

    def setup_layout(self):
       self.main_layout = QVBoxLayout()
       cameras_button = QPushButton('Edit Cameras')
       cameras_button.clicked.connect(open_camera_dialog)
       for camera in get_cameras():
         self.add_camera_row(camera)
       self.main_layout.addWidget(cameras_button)
       self.setLayout(self.main_layout)

    def add_camera_row(self, camera):
       row = QHBoxLayout()
       for preset_number in range(5):
          preset_wrapper = QVBoxLayout()

          image_path = f'{executable_path}images/preset-{camera.camera_number}-{preset_number}.jpg'
          if not path.exists(image_path):
             image_path = f'{executable_path}images/default.jpg'
          recall_button = ImageButton(image_path)
          recall_button.clicked.connect(self.get_preset_function(camera, preset_number))
          preset_wrapper.addWidget(recall_button)

          set_button = QPushButton('Update Preset')
          set_button.clicked.connect(self.get_set_preset_function(camera, preset_number, recall_button))
          preset_wrapper.addWidget(set_button)

          row.addLayout(preset_wrapper)
       row.addLayout(self.create_joystick_layout(camera))

       self.main_layout.addLayout(row)

    def create_joystick_layout(self, camera):
       grid = QGridLayout()
       for row_index, row in enumerate(JOYSTICK_BUTTONS):
         for action_index, action in enumerate(row):
            icon = action
            if action in JOYSTICK_ICONS:
               icon = JOYSTICK_ICONS[action]
            button = QPushButton(icon)
            button.pressed.connect(self.get_move_function(camera, action))
            button.released.connect(self.get_stop_function(camera))
            grid.addWidget(button, row_index, action_index)
       grid.addWidget(QLabel('Speed:'), row_index+1, 0)
       camera.speed_slider = QSlider(Qt.Horizontal)
       camera.speed_slider.setValue(50)
       grid.addWidget(camera.speed_slider, row_index+1, 1, 2, 3)
       return grid

    def get_move_function(self, camera, direction):
       if direction == 'stop':
          return self.get_stop_function(camera)
       if 'focus' in direction:
          return self.get_focus_function(camera, direction)
       def move():
         request = camera.ptz.create_type('ContinuousMove')
         request.ProfileToken = camera.media_profile.token
         velocity = {
            'x': 0,
            'y': 0
         }
         speed = camera.speed_slider.value() / 100
         if 'up' in direction:
            velocity['y'] = camera.YMAX * speed
         elif 'down' in direction:
            velocity['y'] = camera.YMIN * speed
         if 'left' in direction:
            velocity['x'] = camera.XMIN * speed
         elif 'right' in direction:
            velocity['x'] = camera.XMAX * speed
         zoom = None
         if 'zoom+' in direction:
            zoom = camera.ZMAX * speed
         elif 'zoom-' in direction:
            zoom = camera.ZMIN * speed
         request.Velocity = {
            'PanTilt': velocity,
            'Zoom': zoom
         }
         camera.ptz.ContinuousMove(request)

       return move

    def get_stop_function(self, camera):
       def stop():
          camera.ptz.Stop({
             'ProfileToken': camera.media_profile.token
          })
       return stop

    def get_focus_function(self, camera, direction):
       def focus():
          request = camera.imaging.create_type('Move')
          request.VideoSourceToken = camera.video_source_token
          if '+' in direction:
             speed = camera.FMAX
          else:
             speed = camera.FMIN
          request.Focus = {
             'Continuous': {'Speed': speed}
          }
          camera.imaging.Move(request)
       return focus

    def get_preset_function(self, camera, preset_number):
       def trigger_preset():
          try:
            speed = camera.speed_slider.value() / 100
            speed = {
               'PanTilt': {
                  'x': camera.PTSPEED_RANGE * speed,
                  'y': camera.PTSPEED_RANGE * speed
               },
               'Zoom': camera.ZSPEED_RANGE * speed
            }
            camera.ptz.GotoPreset({
               'ProfileToken': camera.media_profile.token,
               'PresetToken': camera.presets[preset_number]['token'],
               'Speed': speed
            })
          except IndexError:
             pass
       return trigger_preset

    def get_set_preset_function(self, camera, preset_number, button):
       def set_preset():
          import cv2
          reload_presets = False
          try:
            preset_token = camera.presets[preset_number]['token']
          except IndexError:
            preset_token = preset_number
            reload_presets = True
          camera.ptz.SetPreset({
             'ProfileToken': camera.media_profile.token,
             'PresetToken': preset_token
          })
          if reload_presets:
            camera.presets = camera.ptz.GetPresets({
               'ProfileToken': camera.media_profile.token
            })
          client = cv2.VideoCapture(camera.stream['Uri'])
          ret, frame = client.read()
          image_path = f'{executable_path}images/preset-{camera.camera_number}-{preset_number}.jpg'
          cv2.imwrite(image_path, frame)
          client.release()
          button.refresh(image_path)
       return set_preset

class CameraDialog(QDialog):
   camera_forms = []

   def __init__(self):
      super().__init__()

      self.main_layout = QVBoxLayout()
      self.form_layout = QVBoxLayout()
      camera_list = get_cameras()
      if len(camera_list):
         for index, camera in enumerate(camera_list):
            self.form_layout.addWidget(
               self.create_camera_form(
                  camera_number=index + 1, camera=camera
               )
            )
      else:
         self.form_layout.addWidget(self.create_camera_form())
      self.main_layout.addLayout(self.form_layout)
      self.main_layout.addWidget(self.create_add_button())
      self.main_layout.addWidget(self.create_save_buttons())
      self.setLayout(self.main_layout)
      self.setWindowTitle('Camera Setup')

   def create_camera_form(self, camera_number=1, camera=None):
      camera_form = QGroupBox(f'Camera {camera_number}')
      layout = QFormLayout()
      name = ''
      ip = '192.168.'
      port = '2000'
      user_name = 'admin'
      password = 'admin'
      if camera:
         name = camera.name
         ip = camera.host
         port = camera.port
         user_name = camera.user
         password = camera.passwd
      layout.addRow(QLabel('Name:'), QLineEdit(text=name))
      layout.addRow(QLabel('IP:'), QLineEdit(text=ip))
      layout.addRow(QLabel('Port:'), QLineEdit(text=str(port)))
      layout.addRow(QLabel("User Name:"), QLineEdit(text=user_name))
      layout.addRow(QLabel("Password:"), QLineEdit(text=password))

      if camera_number > 1:
         remove_button = QPushButton('Remove')
         remove_button.clicked.connect(self.get_remove_camera_method(camera_form))
         layout.addRow(remove_button)

      camera_form.setLayout(layout)
      self.camera_forms.append(camera_form)
      return camera_form

   def create_save_buttons(self):
      save_buttons = QDialogButtonBox(
         QDialogButtonBox.Save | QDialogButtonBox.Cancel
      )
      save_buttons.accepted.connect(self.accept)
      save_buttons.rejected.connect(self.reject)
      return save_buttons

   def create_add_button(self):
      add_button = QPushButton('Add')
      add_button.clicked.connect(self.add_camera_form)
      return add_button

   def add_camera_form(self):
      self.form_layout.addWidget(
         self.create_camera_form(camera_number=len(self.camera_forms) + 1)
      )

   def get_remove_camera_method(self, form):
      dialog = self
      def remove_camera_form(self):
         # TODO: Make the form layout shrink when a form is removed
         dialog.form_layout.removeWidget(form)
         form.deleteLater()
         dialog.camera_forms.remove(form)
         dialog.setLayout(dialog.main_layout)
      return remove_camera_form

   def accept(self):
      db.drop_table('cameras')
      for form in self.camera_forms:
          try:
            fields = form.children()
            camera_data = {
               'name': fields[2].text(),
               'ip': fields[4].text(),
               'port': fields[6].text(),
               'user_name': fields[8].text(),
               'password': fields[10].text()
            }
            cameras_table.insert(camera_data)
          except Exception:
             pass
      setup_cameras()
      return super().accept()


def open_camera_dialog():
   dialog = CameraDialog()
   dialog.exec_()

def main():
   app = QApplication(sys.argv)
   window = MainWindow()
   window.show()
   sys.exit(app.exec_())
	
if __name__ == '__main__':
   main()
