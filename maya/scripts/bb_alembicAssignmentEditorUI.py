
import os
import sys
import functools
import fnmatch
try:
    from PySide2.QtGui import *
    from PySide2.QtCore import *
    from PySide2.QtUiTools import *
    from PySide2.QtWidgets import *
    from shiboken2 import wrapInstance
    #import shiboken
    QApplication.UnicodeUTF8 = 0
    
except:
    #ShpCore.printException(a)
    from PyQt4 import QtCore
    QtCore.Signal = QtCore.pyqtSignal

# remap some often used objects/modules
# Signal = QtCore.Signal
# Qt = QtCore.Qt

sys.path.insert(0, '/home/ashleyr/Dev/bb_python')

from bb_python.gui import Style
from bb_python.gui import MainWindow as BBMainWindow
from bb_python.gui import Widget as BBWidget
from bb_python.Color import Color

try:
    QString = unicode
    _fromUtf8 = QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

ABC_EDITOR_VERSION = "1.0.4"

import cask  # alembic cask helper module
import json  # for deling with the dictionary attributes
import maya.cmds as _mc
import maya.OpenMaya as OpenMaya
import maya.OpenMayaUI as OpenMayaUI

import pymel.core as _pc
in_maya = True

mayaMainWindowPtr = OpenMayaUI.MQtUtil.mainWindow()
mayaMainWindow = wrapInstance(long(mayaMainWindowPtr), QWidget)

draggable = Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled
droppable = Qt.ItemIsDropEnabled
editable = Qt.ItemIsEditable
enabled = Qt.ItemIsEnabled | Qt.ItemIsSelectable
checkable = Qt.ItemIsEnabled | Qt.ItemIsUserCheckable

# need for parsing the ass file, and getting available attributes
from arnold import *


def getArnoldShaders(assFile):

    shaders = []
    displacements = []

    if os.path.isfile(assFile):

        AiBegin()
        # load the plugins
        for p in os.environ['ARNOLD_PLUGIN_PATH'].split(':'):
            AiLoadPlugins(p)
        # load the ass file
        AiASSLoad(assFile, AI_NODE_SHADER)

        # now find all the shaders and displacments

        shaderIter = AiUniverseGetNodeIterator(AI_NODE_SHADER)

        while not AiNodeIteratorFinished(shaderIter):
            this_node = AiNodeIteratorGetNext(shaderIter)
            # get the type of shader
            node_name = AiNodeGetName(this_node)
            node_entry = AiNodeGetNodeEntry(this_node)
            node_type = AiNodeEntryGetName(node_entry)
            if node_type in ['MayaNormalDisplacement']:
                displacements.append((node_name, node_type))
            elif node_type in ['MayaShadingEngine']:
                shaders.append((node_name, node_type))

        AiNodeIteratorDestroy(shaderIter)

        AiEnd()

    return shaders, displacements


def getArnoldEnumOptions(param):

    values = []

    AiBegin()

    for ntype in ['polymesh', 'curves']:
        node_entry = AiNodeEntryLookUp(ntype)

        pentry = AiNodeEntryLookUpParameter(node_entry, param)

        if len(values) == 0 and pentry:
            # get if this is an enum
            if AiParamGetType(pentry) == AI_TYPE_ENUM:
                enum = AiParamGetEnum(pentry)
                values = []
                index = 0
                while True:
                    value = AiEnumGetString(enum, index)
                    index += 1
                    if not value:
                        break
                    values.append(value)

    AiEnd()

    return values


def getArnoldNodeParams(nodename):

    def GetParamValueAsString(pentry, val, type):
        if type == AI_TYPE_BYTE:
            return int(val.contents.BYTE)
        elif type == AI_TYPE_INT:
            return int(val.contents.INT)
        elif type == AI_TYPE_UINT:
            return int(val.contents.UINT)
        elif type == AI_TYPE_BOOLEAN:
            return True if (val.contents.BOOL != 0) else False
        elif type == AI_TYPE_FLOAT:
            return float(val.contents.FLT)
        elif type == AI_TYPE_VECTOR or type == AI_TYPE_POINT:
            return (val.contents.PNT.x, val.contents.PNT.y, val.contents.PNT.z)
        elif type == AI_TYPE_POINT2:
            return (val.contents.PNT.x, val.contents.PNT.y)
        elif type == AI_TYPE_RGB:
            return (val.contents.RGB.r, val.contents.RGB.g, val.contents.RGB.b)
        elif type == AI_TYPE_RGBA:
            return (val.contents.RGBA.r,
                    val.contents.RGBA.g,
                    val.contents.RGBA.b,
                    val.contents.RGBA.a)
        elif type == AI_TYPE_STRING:
            return val.contents.STR
        elif type == AI_TYPE_POINTER:
            return "%p" % val.contents.PTR
        elif type == AI_TYPE_NODE:
            name = AiNodeGetName(val.contents.PTR)
            return str(name)
        elif type == AI_TYPE_ENUM:
            enum = AiParamGetEnum(pentry)
            return AiEnumGetString(enum, val.contents.INT)
        elif type == AI_TYPE_MATRIX:
            return ""
        elif type == AI_TYPE_ARRAY:
            array = val.contents.ARRAY.contents
            nelems = array.nelements
            if nelems == 0:
                return "(empty)"
            elif nelems == 1:
                    if array.type == AI_TYPE_FLOAT:
                        return "%g" % AiArrayGetFlt(array, 0)
                    elif array.type == AI_TYPE_VECTOR:
                        vec = AiArrayGetVec(array, 0)
                        return "%g, %g, %g" % (vec.x, vec.y, vec.z)
                    elif array.type == AI_TYPE_POINT:
                        pnt = AiArrayGetPnt(array, 0)
                        return "%g, %g, %g" % (pnt.x, pnt.y, pnt.z)
                    elif array.type == AI_TYPE_RGB:
                        rgb = AiArrayGetRGB(array, 0)
                        return "%g, %g, %g" % (rgb.r, rgb.g, rgb.b)
                    elif array.type == AI_TYPE_RGBA:
                        rgba = AiArrayGetRGBA(array, 0)
                        return "%g, %g, %g" % (rgba.r, rgba.g, rgba.b, rgba.a)
                    elif array.type == AI_TYPE_POINTER:
                        ptr = cast(AiArrayGetPtr(array, 0), POINTER(AtNode))
                        return "%p" % ptr
                    elif array.type == AI_TYPE_NODE:
                        ptr = cast(AiArrayGetPtr(array, 0), POINTER(AtNode))
                        name = AiNodeGetName(ptr)
                        return str(name)
                    else:
                        return ""
            else:
                return "(%u elements)" % nelems
        else:
            return ""

    nodeInfoDict = {}

    AiBegin()

    node_entry = AiNodeEntryLookUp(nodename)

    if not node_entry:
        AiEnd()
        raise 'Nothing to know about node "%s"' % node

    num_params = AiNodeEntryGetNumParams(node_entry)

    params = []
    for p in range(num_params):
        pentry = AiNodeEntryGetParameter(node_entry, p)
        params.append([AiParamGetName(pentry), p])

    # if sort == 1:
    #    params.sort(lambda x, y: -1 if x[0] < y[0] else 1)

    for pp in params:
        pentry = AiNodeEntryGetParameter(node_entry, pp[1])
        param_type = AiParamGetType(pentry)
        param_value = AiParamGetDefault(pentry)
        param_name = AiParamGetName(pentry)

        if param_type == AI_TYPE_ARRAY:
            # We want to know the type of the elements in the array
            array = param_value.contents.ARRAY.contents
            type_string = "%s[]" % AiParamGetTypeName(array.type)
        else:
            type_string = AiParamGetTypeName(param_type)

        # Print it like: <type> <name> <default>
        default = GetParamValueAsString(pentry, param_value, param_type)

        nodeInfoDict[param_name] = {'type': type_string,
                                    'default': default}

    AiEnd()

    return nodeInfoDict

# ---------------- WIDGETS ------------------- #


def clearWidget(widget):
    """Utility method for clearing a widget and any widgets it contains"""
    while widget.layout().count():
        item = widget.layout().takeAt(0)
        if isinstance(item, QWidgetItem):
            item.widget().close()
        elif isinstance(item, QSpacerItem):
            widget.layout().removeItem(item)


def getMayaWindow():
    """
    Get the main Maya window as a QMainWindow instance
    @return: QMainWindow instance of the top level Maya windows
    """
    ptr = OpenMaya.MQtUtil.mainWindow()
    if ptr is not None:
        return wrapinstance(long(ptr), QWidget)


def toQtObject(mayaName):
    '''
    Given the name of a Maya UI element of any type,
    return the corresponding QWidget or QAction.
    If the object does not exist, returns None
    '''
    import shiboken
    import maya.OpenMayaUI as apiUI

    ptr = apiUI.MQtUtil.findControl(mayaName)
    if ptr is None:
        ptr = apiUI.MQtUtil.findLayout(mayaName)
        if ptr is None:
            ptr = apiUI.MQtUtil.findMenuItem(mayaName)
          
    if ptr is not None:
        obj = shiboken.wrapInstance(long(ptr), QObject)
        return obj

# Overrides Widgets


class FloatLabelWidget(QFrame):
    """ docstring for FloatLabelWidget"""

    valueChanged = Signal(str, str, str, float)
    deleteAttr = Signal(str, str, str)

    def __init__(self, title='test', parent=None):
        QFrame.__init__(self)
        self.setLayout(QHBoxLayout())
        self.label = QLabel(title)
        self.layout().addWidget(self.label)
        self.valueWidget = QDoubleSpinBox()
        self.layout().addWidget(self.valueWidget)

        self.removeWidget = QPushButton()
        BBWidget.setStaticSize(self.removeWidget, 15, 15)
        self.removeWidget.setFlat(True)
        self.removeWidget.setStyleSheet(
            "QPushButton:flat {border: 0px solid rgb(0,0,0,0);background-color: rgba(0,0,0,0);}")
        self.removeWidget.setIcon(
            QIcon(self.style().standardPixmap(QStyle.SP_DockWidgetCloseButton)))
        self.removeWidget.setToolTip("Remove attribute from item")
        self.removeWidget.clicked.connect(self.emitDelete)
        self.layout().addWidget(self.removeWidget)

        self.node = None
        self.pattern = None
        self.attr = None

        self.valueWidget.valueChanged[float].connect(self.emitValue)

    def getValue(self):
        return self.valueWidget.value()

    def setValue(self, value):
        self.valueWidget.setValue(value)

    def emitValue(self, value):
        self.valueChanged.emit(self.node, self.pattern, self.attr, float(value))

    def emitDelete(self, *args):
        self.deleteAttr.emit(self.node, self.pattern, self.attr)


class IntLabelWidget(QFrame):
    """docstring for IntLabelWidget"""
    valueChanged = Signal(str, str, str, int)
    deleteAttr = Signal(str, str, str)

    def __init__(self, title='test', parent=None):
        QFrame.__init__(self)
        self.setLayout(QHBoxLayout())
        self.label = QLabel(title)
        self.layout().addWidget(self.label)
        self.valueWidget = QSpinBox()
        self.layout().addWidget(self.valueWidget)

        self.removeWidget = QPushButton()
        BBWidget.setStaticSize(self.removeWidget, 15, 15)
        self.removeWidget.setFlat(True)
        self.removeWidget.setStyleSheet(
            "QPushButton:flat {border: 0px solid rgb(0,0,0,0);background-color: rgba(0,0,0,0);}")
        self.removeWidget.setIcon(
            QIcon(self.style().standardPixmap(QStyle.SP_DockWidgetCloseButton)))
        self.removeWidget.setToolTip("Remove attribute from item")
        self.removeWidget.clicked.connect(self.emitDelete)
        self.layout().addWidget(self.removeWidget)

        self.node = None
        self.pattern = None
        self.attr = None

        self.valueWidget.valueChanged[int].connect(self.emitValue)

    def getValue(self):
        return self.valueWidget.value()

    def setValue(self, value):
        self.valueWidget.setValue(value)

    def emitValue(self, value):
        self.valueChanged.emit(self.node, self.pattern, self.attr, int(value))

    def emitDelete(self, *args):
        self.deleteAttr.emit(self.node, self.pattern, self.attr)


class BoolLabelWidget(QFrame):
    """docstring for IntLabelWidget"""
    valueChanged = Signal(str, str, str, bool)
    deleteAttr = Signal(str, str, str)

    def __init__(self, title='test', parent=None):
        QFrame.__init__(self)
        self.setLayout(QHBoxLayout())
        self.label = QLabel(title)
        self.layout().addWidget(self.label)
        self.valueWidget = QCheckBox()
        self.layout().addWidget(self.valueWidget)

        self.removeWidget = QPushButton()
        BBWidget.setStaticSize(self.removeWidget, 15, 15)
        self.removeWidget.setFlat(True)
        self.removeWidget.setStyleSheet(
            "QPushButton:flat {border: 0px solid rgb(0,0,0,0);background-color: rgba(0,0,0,0);}")
        self.removeWidget.setIcon(
            QIcon(self.style().standardPixmap(QStyle.SP_DockWidgetCloseButton)))
        self.removeWidget.setToolTip("Remove attribute from item")
        self.removeWidget.clicked.connect(self.emitDelete)
        self.layout().addWidget(self.removeWidget)

        self.node = None
        self.pattern = None
        self.attr = None

        self.valueWidget.stateChanged.connect(self.emitValue)

    def getValue(self):
        return self.valueWidget.isChecked()

    def setValue(self, value):
        self.valueWidget.setChecked(value)

    def emitValue(self, value):
        val = bool(value)
        self.valueChanged.emit(self.node, self.pattern, self.attr, value)

    def emitDelete(self, *args):
        self.deleteAttr.emit(self.node, self.pattern, self.attr)


class EnumLabelWidget(QFrame):
    """docstring for IntLabelWidget"""

    valueChanged = Signal(str, str, str, str)
    deleteAttr = Signal(str, str, str)

    def __init__(self, title='test', parent=None, options=[]):
        QFrame.__init__(self)
        self.setLayout(QHBoxLayout())
        self.label = QLabel(title)
        self.layout().addWidget(self.label)
        self.valueWidget = QComboBox()
        self.layout().addWidget(self.valueWidget)

        self.removeWidget = QPushButton()
        BBWidget.setStaticSize(self.removeWidget, 15, 15)
        self.removeWidget.setFlat(True)
        self.removeWidget.setStyleSheet(
            "QPushButton:flat {border: 0px solid rgb(0,0,0,0);background-color: rgba(0,0,0,0);}")
        self.removeWidget.setIcon(
            QIcon(self.style().standardPixmap(QStyle.SP_DockWidgetCloseButton)))
        self.removeWidget.setToolTip("Remove attribute from item")
        self.removeWidget.clicked.connect(self.emitDelete)
        self.layout().addWidget(self.removeWidget)

        self.node = None
        self.pattern = None
        self.attr = None

        self.setOptions(options)

        self.valueWidget.currentIndexChanged[str].connect(self.emitValue)

    def setOptions(self, optionsList):
        for i in range(self.valueWidget.count()):
            self.valueWidget.removeItem(i)
        for opt in optionsList:
            self.valueWidget.addItem(opt)

    def getValue(self):
        return self.valueWidget.currentText()

    def setValue(self, value):
        idx = self.valueWidget.findText(value)
        if idx != -1:
            self.valueWidget.setCurrentIndex(idx)

    def emitValue(self, value):
        self.valueChanged.emit(self.node, self.pattern, self.attr, str(value))

    def emitDelete(self, *args):
        self.deleteAttr.emit(self.node, self.pattern, self.attr)


class VisibilityLabelWidget(QFrame):
    """docstring for VisibilityLabelWidget"""

    valueChanged = Signal(str, str, str, int)
    deleteAttr = Signal(str, str, str)

    def __init__(self, title='test', parent=None):
        QFrame.__init__(self)
        self.setLayout(QVBoxLayout())
        self.label_frame = QFrame()
        self.label_frame.setStyleSheet("QFrame {border:0px;background-color: rgba(0,0,0,0);}")
        self.label_frame.setLayout(QHBoxLayout())
        self.label_frame.layout().setContentsMargins(0, 0, 0, 0)
        self.label = QLabel(title)
        self.label_frame.layout().addWidget(self.label)

        self.removeWidget = QPushButton()
        BBWidget.setStaticSize(self.removeWidget, 15, 15)
        self.removeWidget.setFlat(True)
        self.removeWidget.setStyleSheet(
            "QPushButton:flat {border: 0px solid rgb(0,0,0,0);background-color: rgba(0,0,0,0);}")
        self.removeWidget.setIcon(
            QIcon(self.style().standardPixmap(QStyle.SP_DockWidgetCloseButton)))
        self.removeWidget.setToolTip("Remove attribute from item")
        self.removeWidget.clicked.connect(self.emitDelete)
        self.label_frame.layout().addWidget(self.removeWidget)

        self.layout().addWidget(self.label_frame)

        self.node = None
        self.pattern = None
        self.attr = None

        # make a box per visability option
        self.visBoxCamera = QCheckBox("Camera")
        self.visBoxCamera.setChecked(True)
        self.layout().addWidget(self.visBoxCamera)
        self.visBoxShadow = QCheckBox("Shadow")
        self.visBoxShadow.setChecked(True)
        self.layout().addWidget(self.visBoxShadow)
        self.visBoxReflect = QCheckBox("Reflect")
        self.visBoxReflect.setChecked(True)
        self.layout().addWidget(self.visBoxReflect)
        self.visBoxRefract = QCheckBox("Refract")
        self.visBoxRefract.setChecked(True)
        self.layout().addWidget(self.visBoxRefract)
        self.visBoxDiffuse = QCheckBox("Diffuse")
        self.visBoxDiffuse.setChecked(True)
        self.layout().addWidget(self.visBoxDiffuse)
        self.visBoxGlossy = QCheckBox("Glossy")
        self.visBoxGlossy.setChecked(True)
        self.layout().addWidget(self.visBoxGlossy)

        self.visBoxCamera.stateChanged.connect(self.emitValue)
        self.visBoxShadow.stateChanged.connect(self.emitValue)
        self.visBoxReflect.stateChanged.connect(self.emitValue)
        self.visBoxRefract.stateChanged.connect(self.emitValue)
        self.visBoxDiffuse.stateChanged.connect(self.emitValue)
        self.visBoxGlossy.stateChanged.connect(self.emitValue)

    def getValue(self):

        vis = AI_RAY_ALL

        if not self.visBoxCamera.isChecked():
            vis &= ~AI_RAY_CAMERA
        if not self.visBoxShadow.isChecked():
            vis &= ~AI_RAY_SHADOW
        if not self.visBoxReflect.isChecked():
            vis &= ~AI_RAY_REFLECTED
        if not self.visBoxRefract.isChecked():
            vis &= ~AI_RAY_REFRACTED
        if not self.visBoxDiffuse.isChecked():
            vis &= ~AI_RAY_DIFFUSE
        if not self.visBoxGlossy.isChecked():
            vis &= ~AI_RAY_GLOSSY

        return vis
   
    def setValue(self, value):
        compViz = AI_RAY_ALL
        if value < compViz:
            compViz &= ~AI_RAY_GLOSSY
            if value <= compViz:
                self.visBoxGlossy.setChecked(False)
            else:
                compViz += AI_RAY_GLOSSY
            compViz &= ~AI_RAY_DIFFUSE
            if value <= compViz:
                self.visBoxDiffuse.setChecked(False)
            else:
                compViz += AI_RAY_DIFFUSE
            compViz &= ~AI_RAY_REFRACTED
            if value <= compViz:
                self.visBoxRefract.setChecked(False)
            else:
                compViz += AI_RAY_REFRACTED
            compViz &= ~AI_RAY_REFLECTED
            if value <= compViz:
                self.visBoxReflect.setChecked(False)
            else:
                compViz += AI_RAY_REFLECTED
            compViz &= ~AI_RAY_SHADOW
            if value <= compViz:
                self.visBoxShadow.setChecked(False)
            else:
                compViz += AI_RAY_SHADOW
            compViz &= ~AI_RAY_CAMERA
            if value <= compViz:
                self.visBoxCamera.setChecked(False)

    def emitValue(self, *args):
        self.valueChanged.emit(self.node,
                               self.pattern,
                               self.attr,
                               self.getValue())

    def emitDelete(self, *args):
        self.deleteAttr.emit(self.node, self.pattern, self.attr)


class ClickableLabel(QLabel):
    """docstring for ShpClickableLabel"""

    clicked = Signal()  # emit collapsed True if the frame is collapsed

    def __init__(self, title):
        super(ClickableLabel, self).__init__(title)

    def mousePressEvent(self, event):
        self.clicked.emit()

# User Attributes Widgets


class UserFloatAttrBox(QFrame):
    """docstring for UserFloatAttrBox"""
    valueChanged = Signal(str, str, str, float)
    attrChanged = Signal(str, str, str, str)
    deleteAttr = Signal(str, str, str)

    def __init__(self, parent=None):
        QFrame.__init__(self)
        self.setLayout(QHBoxLayout())
        self.attrNameWidget = QLineEdit()
        self.layout().addWidget(self.attrNameWidget)
        self.valueWidget = QDoubleSpinBox()
        self.layout().addWidget(self.valueWidget)

        self.removeWidget = QPushButton()
        BBWidget.setStaticSize(self.removeWidget, 15, 15)
        self.removeWidget.setFlat(True)
        self.removeWidget.setStyleSheet(
            "QPushButton:flat {border: 0px solid rgb(0,0,0,0);background-color: rgba(0,0,0,0);}")
        self.removeWidget.setIcon(
            QIcon(self.style().standardPixmap(QStyle.SP_DockWidgetCloseButton)))
        self.removeWidget.setToolTip("Remove attribute from item")
        self.removeWidget.clicked.connect(self.emitDelete)
        self.layout().addWidget(self.removeWidget)

        self.node = None
        self.pattern = None
        self.attr = None

        self.valueWidget.valueChanged[float].connect(self.emitValue)
        self.attrNameWidget.textChanged.connect(self.emitAttrNameChange)

    def getValue(self):
        return self.valueWidget.value()

    def setValue(self, value):
        self.valueWidget.setValue(value)

    def getAttrName(self):
        return self.attrNameWidget.text()

    def setAttrName(self, value):
        self.attrNameWidget.setText(value)

    def emitValue(self, value):
        self.valueChanged.emit(self.node, self.pattern, self.attr, float(value))

    def emitAttrNameChange(self, value):
        self.attrChanged.emit(self.node, self.pattern, self.attr, value)
        self.attr = value  # set the attr varibale to the new name

    def emitDelete(self, *args):
        self.deleteAttr.emit(self.node, self.pattern, self.attr)


class UserIntAttrBox(QFrame):
    """docstring for IntLabelWidget"""

    valueChanged = Signal(str, str, str, int)
    attrChanged = Signal(str, str, str, str)
    deleteAttr = Signal(str, str, str)

    def __init__(self, title='test', parent=None):
        QFrame.__init__(self)
        self.setLayout(QHBoxLayout())
        self.attrNameWidget = QLineEdit()
        self.layout().addWidget(self.attrNameWidget)
        self.valueWidget = QSpinBox()
        self.layout().addWidget(self.valueWidget)

        self.removeWidget = QPushButton()
        BBWidget.setStaticSize(self.removeWidget, 15, 15)
        self.removeWidget.setFlat(True)
        self.removeWidget.setStyleSheet(
            "QPushButton:flat {border: 0px solid rgb(0,0,0,0);background-color: rgba(0,0,0,0);}")
        self.removeWidget.setIcon(
            QIcon(self.style().standardPixmap(QStyle.SP_DockWidgetCloseButton)))
        self.removeWidget.setToolTip("Remove attribute from item")
        self.removeWidget.clicked.connect(self.emitDelete)
        self.layout().addWidget(self.removeWidget)

        self.node = None
        self.pattern = None
        self.attr = None

        self.valueWidget.valueChanged[int].connect(self.emitValue)
        self.attrNameWidget.textChanged.connect(self.emitAttrNameChange)

    def getValue(self):
        return self.valueWidget.value()

    def setValue(self, value):
        self.valueWidget.setValue(value)

    def getAttrName(self):
        return self.attrNameWidget.text()

    def setAttrName(self, value):
        self.attrNameWidget.setText(value)

    def emitValue(self, value):
        self.valueChanged.emit(self.node, self.pattern, self.attr, int(value))

    def emitAttrNameChange(self, value):
        self.attrChanged.emit(self.node, self.pattern, self.attr, value)
        self.attr = value  # set the attr varibale to the new name

    def emitDelete(self, *args):
        self.deleteAttr.emit(self.node, self.pattern, self.attr)


class UserBoolAttrBox(QFrame):
    """docstring for IntLabelWidget"""

    valueChanged = Signal(str, str, str, bool)
    attrChanged = Signal(str, str, str, str)
    deleteAttr = Signal(str, str, str)

    def __init__(self, parent=None):
        QFrame.__init__(self)
        self.setLayout(QHBoxLayout())
        self.attrNameWidget = QLineEdit()
        self.layout().addWidget(self.attrNameWidget)
        self.valueWidget = QCheckBox()
        self.layout().addWidget(self.valueWidget)

        self.removeWidget = QPushButton()
        BBWidget.setStaticSize(self.removeWidget, 15, 15)
        self.removeWidget.setFlat(True)
        self.removeWidget.setStyleSheet(
            "QPushButton:flat {border: 0px solid rgb(0,0,0,0);background-color: rgba(0,0,0,0);}")
        self.removeWidget.setIcon(
            QIcon(self.style().standardPixmap(QStyle.SP_DockWidgetCloseButton)))
        self.removeWidget.setToolTip("Remove attribute from item")
        self.removeWidget.clicked.connect(self.emitDelete)
        self.layout().addWidget(self.removeWidget)

        self.node = None
        self.pattern = None
        self.attr = None

        self.valueWidget.stateChanged.connect(self.emitValue)
        self.attrNameWidget.textChanged.connect(self.emitAttrNameChange)

    def getValue(self):
        return self.valueWidget.isChecked()

    def setValue(self, value):
        self.valueWidget.setChecked(value)

    def getAttrName(self):
        return self.attrNameWidget.text()

    def setAttrName(self, value):
        self.attrNameWidget.setText(value)

    def emitValue(self, value):
        val = bool(value)
        self.valueChanged.emit(self.node, self.pattern, self.attr, value)

    def emitAttrNameChange(self, value):
        self.attrChanged.emit(self.node, self.pattern, self.attr, value)
        self.attr = value  # set the attr varibale to the new name

    def emitDelete(self, *args):
        self.deleteAttr.emit(self.node, self.pattern, self.attr)


class UserStringAttrBox(QFrame):
    """ docstring for IntLabelWidget"""
    valueChanged = Signal(str, str, str, str)
    attrChanged = Signal(str, str, str, str)
    deleteAttr = Signal(str, str, str)

    def __init__(self, parent=None):
        QFrame.__init__(self)
        self.setLayout(QHBoxLayout())
        self.attrNameWidget = QLineEdit()
        self.layout().addWidget(self.attrNameWidget)
        self.valueWidget = QLineEdit()
        self.layout().addWidget(self.valueWidget)

        self.removeWidget = QPushButton()
        BBWidget.setStaticSize(self.removeWidget, 15, 15)
        self.removeWidget.setFlat(True)
        self.removeWidget.setStyleSheet(
            "QPushButton:flat {border: 0px solid rgb(0,0,0,0);background-color: rgba(0,0,0,0);}")
        self.removeWidget.setIcon(
            QIcon(self.style().standardPixmap(QStyle.SP_DockWidgetCloseButton)))
        self.removeWidget.setToolTip("Remove attribute from item")
        self.removeWidget.clicked.connect(self.emitDelete)
        self.layout().addWidget(self.removeWidget)

        self.node = None
        self.pattern = None
        self.attr = None

        self.valueWidget.textChanged.connect(self.emitValue)
        self.attrNameWidget.textChanged.connect(self.emitAttrNameChange)

    def getValue(self):
        return self.valueWidget.text()

    def setValue(self, value):
        self.valueWidget.setText(value)

    def getAttrName(self):
        return self.attrNameWidget.text()

    def setAttrName(self, value):
        self.attrNameWidget.setText(value)
        self.attr = value

    def emitValue(self, value):
        self.valueChanged.emit(self.node, self.pattern, self.attr, value)

    def emitAttrNameChange(self, value):
        self.attrChanged.emit(self.node, self.pattern, self.attr, value)
        self.attr = value  # set the attr varibale to the new name

    def emitDelete(self, *args):
        self.deleteAttr.emit(self.node, self.pattern, self.attr)


class UserStringArrayAttrBox(QFrame):
    """docstring for UserStringArrayAttrBox"""
    valueChanged = Signal(str, str, str, list)
    attrChanged = Signal(str, str, str, str)
    deleteAttr = Signal(str, str, str)

    def __init__(self, parent=None):
        QFrame.__init__(self)
        self.setLayout(QHBoxLayout())

        # v Box for adding / removing items from list

        self.label_button_box = QWidget(self)
        self.label_button_box.setLayout(QVBoxLayout())

        self.attrNameWidget = QLineEdit()
        self.label_button_box.layout().addWidget(self.attrNameWidget)

        self.addItemButton = QPushButton("Add String")
        self.addItemButton.setToolTip("Add new item to the string list")
        self.label_button_box.layout().addWidget(self.addItemButton)
        self.removeItemButton = QPushButton("Remove String")
        self.removeItemButton.setToolTip("Remove the currently selected Item from the string list")
        self.label_button_box.layout().addWidget(self.removeItemButton)

        self.label_button_box.layout().insertStretch(-1)

        self.layout().addWidget(self.label_button_box)

        self.valueWidget = QListWidget(self)
        self.layout().addWidget(self.valueWidget)

        self.removeWidget = QPushButton()
        BBWidget.setStaticSize(self.removeWidget, 15, 15)
        self.removeWidget.setFlat(True)
        self.removeWidget.setStyleSheet(
            "QPushButton:flat {border: 0px solid rgb(0,0,0,0);background-color: rgba(0,0,0,0);}")
        self.removeWidget.setIcon(
            QIcon(self.style().standardPixmap(QStyle.SP_DockWidgetCloseButton)))
        self.removeWidget.setToolTip("Remove attribute from item")
        self.removeWidget.clicked.connect(self.emitDelete)
        self.layout().addWidget(self.removeWidget)

        self.node = None
        self.pattern = None
        self.attr = None

        self.valueWidget.itemChanged.connect(self.emitValue)
        self.attrNameWidget.textChanged.connect(self.emitAttrNameChange)

        self.addItemButton.clicked.connect(self.addString)
        self.removeItemButton.clicked.connect(self.removeString)

    def addString(self):
        label = '#' + str(self.valueWidget.count() + 1)
        self.valueWidget.addItem(label)
        i = self.valueWidget.item(self.valueWidget.count() - 1)
        i.setFlags(editable | enabled)
        self.emitValue()

    def removeString(self):
        self.valueWidget.takeItem(self.valueWidget.currentRow())
        self.emitValue()

    def getValue(self):
        return self.valueWidget.text()

    def setValue(self, value):
        self.valueWidget.addItems(value)
        for i in range(self.valueWidget.count()):
            self.valueWidget.item(i).setFlags(editable | enabled)

    def getAttrName(self):
        return self.attrNameWidget.text()

    def setAttrName(self, value):
        self.attrNameWidget.setText(value)
        self.attr = value

    def emitValue(self, value=None):
        # get the current string list
        string_list = []
        for i in range(self.valueWidget.count()):
            string_list.append(self.valueWidget.item(i).text())
        self.valueChanged.emit(self.node, self.pattern, self.attr, string_list)

    def emitAttrNameChange(self, value):
        self.attrChanged.emit(self.node, self.pattern, self.attr, value)
        self.attr = value  # set the attr varibale to the new name

    def emitDelete(self, *args):
        self.deleteAttr.emit(self.node, self.pattern, self.attr)

# Misc Widgets


class AttrCollapseFrame(QFrame):

    collaped = Signal(bool)  # emit collapsed True if the frame is collapsed
    expanded = Signal(bool)  # emit expanded True if the frame is expanded

    def __init__(self, title="test", parent=None):
        QFrame.__init__(self, parent)
        self.setObjectName('BBCollapseFrame')
        
        # set-up internal layout
        
        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        
        # title widget holder
        
        self.titleWidget = QWidget(self)
        self.titleWidget.setObjectName('BBCollapseTitleWidget')
        self.titleWidget.setStyleSheet("QWidget#BBCollapseTitleWidget {background:rgba(0,0,0,0)}")
        self.titleWidget.setLayout(QHBoxLayout())
        self.titleWidget.layout().setContentsMargins(0, 0, 0, 0)
        
        # append a collapse icon and label
        
        self.collapseButton = BBWidget.BBPushButton('+')
        self.collapseButton.setFlat(True)
        self.collapseButton.setObjectName("BBCollapseButton")
        self.collapseButton.setStyleSheet(
            """QPushButton#BBCollapseButton {border: 1px solid rgb(0,0,0);
            font-weight: bold;font-size: 12px}""")
        BBWidget.setStaticSize(self.collapseButton, 15, 15)
        
        self.titleLabel = ClickableLabel(title)
        # self.titleLabel.setStyleSheet("QLabel {color:rgb(200,200,200);background:rgba(0,0,0,0)}")
        self.titleLabel.setSizePolicy(QSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum))

        self.titleWidget.layout().addWidget(self.collapseButton)
        self.titleWidget.layout().addWidget(self.titleLabel)
        self.titleWidget.layout().insertStretch(-1)
        
        self.layout().addWidget(self.titleWidget)
        
        # make internal widget with horizontal layout that can be hidden
                      
        self.centreWidget = QFrame(self)
        self.centreWidget.setObjectName('BBCollapseFrameCentre')
        self.centreLayout = QVBoxLayout()
        self.centreWidget.setLayout(self.centreLayout)
#        self.centreWidget.layout().setContentsMargins(0,0,0,0)
        self.setStyleSheet("QFrame#BBCollapseFrame {background:rgba(0,0,0,0)}"
                           "QFrame#BBCollapseFrameCentre {border: 1px solid rgb(125,125,125);}"
                           "QWidget {color:rgba(200,200,200,255)}")
        
        self.centreWidget.setHidden(True)
        
        self.layout().addWidget(self.centreWidget)

        self.collapseButton.clicked.connect(self.toggle)
        self.titleLabel.clicked.connect(self.toggle)
    
    def isCollapsed(self):
        
        if self.centreWidget.isHidden():
            return True
        else:
            return False
    
    def toggle(self):
        """Toggle the collapsed state of the widget"""
        if self.isCollapsed():
            # open the widget
            self.centreWidget.setVisible(True)
            self.collapseButton.setText('-')
            self.expanded.emit(True)
        else:
            # close the widget
            self.centreWidget.setHidden(True)
            self.collapseButton.setText('+')
            self.collaped.emit(True)

    def setCollapsed(self):
        if not self.isCollapsed():
            self.centreWidget.setHidden(True)
            self.collapseButton.setText('+')
            self.collaped.emit(True)

    def setExpanded(self):
        if self.isCollapsed():
            self.centreWidget.setVisible(True)
            self.collapseButton.setText('-')
            self.expanded.emit(True)

    def setTitle(self, title):
        """set the title of the collapse box"""
        self.titleLabel.setText(title)

    def addWidget(self, widget):
        """ Add wiodget to the central widget"""
        self.centreWidget.layout().addWidget(widget)
    
    def title(self):
        return str(self.titleLabel.text())

# Chooser Dialogs


class OverrideChooser(BBWidget.BBDialog):
    """docstring for OverrideChooser"""
    def __init__(self, title="Override Chooser", parent=None):
        super(OverrideChooser, self).__init__(title, parent)

        self.polymesh_dict = {}
        self.curves_dict = {}

        self.setupUI()

    def setupUI(self):

        self.overridesListBox = QListWidget()
        self.overridesListBox.setSelectionMode(QAbstractItemView.MultiSelection)
        # get the overrides
        self.polymesh_dict = getArnoldNodeParams('polymesh')
        self.curves_dict = getArnoldNodeParams('curves')

        self.allParams = self.polymesh_dict.copy()
        self.allParams.update(self.curves_dict)

        # loop over them and add them to the list box
        for override in sorted(self.allParams):
            if not self.allParams[override]['type'].endswith('[]') and \
               'NODE' not in self.allParams[override]['type']:
                this_itm = self.overridesListBox.addItem(override)

        self.layout().addWidget(self.overridesListBox)

        # bottom panel
        self.acceptButton = QPushButton('Accept')
        self.acceptButton.clicked.connect(self.accept)

        self.layout().addWidget(self.acceptButton)

    @staticmethod
    def getOverrides(parent=None):
        dialog = OverrideChooser(parent=parent)
        result = dialog.exec_()
        overridesListBox = dialog.overridesListBox
        overrides = {i.text(): dialog.allParams[i.text()] for i in overridesListBox.selectedItems()}
        return overrides


class UserAttrChooser(BBWidget.BBDialog):
    """docstring for UserAttrChooser"""
    def __init__(self, title="User Attribute Chooser", parent=None):
        super(UserAttrChooser, self).__init__(title, parent)

        self.setupUI()

    def setupUI(self):

        self.attrListBox = QListWidget()
        # loop over them and add them to the list box
        for attr_type in sorted(['INT', 'FLOAT', 'BOOL', 'STRING', 'STRING ARRAY']):
            this_itm = self.attrListBox.addItem(attr_type)

        self.layout().addWidget(self.attrListBox)

        # bottom panel
        self.acceptButton = QPushButton('Accept')
        self.acceptButton.clicked.connect(self.accept)

        self.layout().addWidget(self.acceptButton)

    @staticmethod
    def getAttr(parent=None):
        dialog = UserAttrChooser(parent=parent)
        result = dialog.exec_()
        attr_type = dialog.attrListBox.currentItem().text()
        return attr_type


class ShadersChooser(BBWidget.BBDialog):
    """docstring for ShadersChooser"""
    def __init__(self, title="Shader Chooser", parent=None, node=None):
        super(ShadersChooser, self).__init__(title, parent)
    
        self.setupUI(node)
    
    def setupUI(self, node):
    
        self.shadersListBox = QListWidget()
        # get the shading groups in the scene
        shadingEngines = _mc.ls(type='shadingEngine')
          
        for se in shadingEngines:
            self.shadersListBox.addItem(se)
    
        assShaders = getArnoldShaders(node.assShaders.get())[0]
        if len(assShaders):
            for se in assShaders:
                self.shadersListBox.addItem(se[0])
    
        # bottom panel
        self.acceptButton = QPushButton('Accept')
        self.acceptButton.clicked.connect(self.accept)
    
        self.layout().addWidget(self.shadersListBox)
        self.layout().addWidget(self.acceptButton)
    
    @staticmethod
    def getShader(parent=None, node=None):
        dialog = ShadersChooser(parent=parent, node=node)
        result = dialog.exec_()
        if result == QDialog.Accepted:
            shader = dialog.shadersListBox.currentItem().text()
            return shader


class DisplacementChooser(BBWidget.BBDialog):
    """docstring for DisplacementChooser"""
    def __init__(self, title="Shader Chooser", parent=None, node=None):
        super(DisplacementChooser, self).__init__(title, parent)

        self.setupUI(node)

    def setupUI(self, node):

        self.shadersListBox = QListWidget()
        # get the shading groups in the scene
        displacements = _mc.ls(type='displacementShader')
        for se in displacements:
            self.shadersListBox.addItem("{}.displacement".format(se))

        assDisplacements = getArnoldShaders(node.assShaders.get())[1]
        if len(assDisplacements):
            for se in assDisplacements:
                self.shadersListBox.addItem(se[0])

        # bottom panel
        self.acceptButton = QPushButton('Accept')
        self.acceptButton.clicked.connect(self.accept)

        self.layout().addWidget(self.shadersListBox)
        self.layout().addWidget(self.acceptButton)

    @staticmethod
    def getShader(parent=None, node=None):
        dialog = DisplacementChooser(parent=parent, node=node)
        result = dialog.exec_()
        if result == QDialog.Accepted:
            shader = dialog.shadersListBox.currentItem().text()
            return shader


class ExpressionCheckerDialog(BBWidget.BBDialog):
    """  docstring for ExpressionCheckerDialog"""
    def __init__(self, expression='*', abcfile='', startpoint='/',
                 title="Expression Checker", parent=None):
        super(ExpressionCheckerDialog, self).__init__(title, parent)

        self.expression = expression
        self.abcfile = abcfile
        self.startpoint = startpoint

        self.setupUI()

    def setupUI(self):
        self.treeWidget = QTreeWidget()
        self.treeWidget.setItemHidden(self.treeWidget.headerItem(), True)
    
        a = cask.Archive(self.abcfile).top
        # get to the start point
        if self.startpoint not in ['/', '']:
            a = self.getObject(a, self.startpoint)
    
        abc_item = self.walktree(a)  # walk the graph
    
        self.treeWidget.addTopLevelItem(abc_item)
        abc_item.setExpanded(True)
    
        self.layout().addWidget(self.treeWidget)
    
    def getObject(self, obj, targetPath):
    
        out_obj = None
        for c in obj.children.values():
            this_path = c.path()
            if this_path == targetPath:
                return c
            else:
                out_obj = self.getObject(c, targetPath)
                if out_obj:
                    return out_obj
          
        return None
             
    def walktree(self, iobject):
        """
        Walk the tree of nodes in the alembic file
        """
    
        item = QTreeWidgetItem()
        item.setText(0, str(iobject.name))
        item.match = False
        item.childmatch = False
        fullpath = str(iobject.path())
        # check if the path matches the pattern, if so set the background colour
        if fnmatch.fnmatch(fullpath, self.expression):
            item.setForeground(0, QBrush(QColor(119, 119, 225)))
            item.match = True

        item.fullPath = fullpath
        item.type = 'iobject'
        for child in iobject.children.values():
            childItem = self.walktree(child)
            item.addChild(childItem)
            if not item.match and (childItem.match is True or childItem.childmatch is True):
                item.childmatch = True
                item.setForeground(0, QBrush(QColor(180, 180, 225)))
                item.setBackground(0, QBrush(QColor(80, 80, 80)))
    
        return item

#################
#  Main Window  #
#################


TITLE = 'Alembic Editor {} ( using alembic {})'.format(
    ABC_EDITOR_VERSION, cask.Archive().using_version())


class AlembicEditorWindow(BBMainWindow.BlueBoltWindow):
    """Base class for alemic editor window"""

    nodes = ['ieProceduralHolder', 'bb_alembicArchiveNode', 'gpuCache']

    # Signals
    selectedNode = Signal(list)

    def __init__(self, parent=None, style=None, title=TITLE):
        super(AlembicEditorWindow, self).__init__(parent=parent, title=title, style=style)
   
        self.currentSelection = []

        self.resize(800, 600)  # default window size

        self.centralwidget = QWidget(self)
        self.setCentralWidget(self.centralwidget)
        self.mainLayout = QVBoxLayout(self.centralwidget)
        self.setAttribute(Qt.WA_DeleteOnClose, True)

        polymesh_dict = getArnoldNodeParams('polymesh')
        curves_dict = getArnoldNodeParams('curves')

        self.allParams = polymesh_dict.copy()
        self.allParams.update(curves_dict)

        self.setupUI()

        self.setupActions()
        self.setupConnections()
        self.refreshUI(self.getSelected())

    def setupUI(self):

        # Top bar
        self.topBar = QFrame()
        self.topBar.setLayout(QHBoxLayout())
        self.refreshSelectionButton = QPushButton("Refresh")
        self.topBar.layout().addWidget(self.refreshSelectionButton)
        self.topBar.layout().insertStretch(-1)

        self.mainLayout.addWidget(self.topBar)

        # treeview
        # ---------------------------------------
        # |object tree | shaders | displacments |
        # ---------------------------------------
        self.treeWidget = QTreeWidget(self.centralwidget)
        self.treeWidget.headerItem().setText(
            0, QApplication.translate("MainWindow", "Object",
                                      None, QApplication.UnicodeUTF8))
        self.treeWidget.setColumnWidth(0, 200)
        self.treeWidget.headerItem().setText(
            1, QApplication.translate("MainWindow", "Shaders",
                                      None, QApplication.UnicodeUTF8))
        self.treeWidget.headerItem().setText(
            2, QApplication.translate("MainWindow", "Displacements",
                                      None, QApplication.UnicodeUTF8))
        self.treeWidget.headerItem().setText(
            3, QApplication.translate("MainWindow", "Overrides",
                                      None, QApplication.UnicodeUTF8))
        self.treeWidget.headerItem().setText(
            4, QApplication.translate("MainWindow", "User Attributes",
                                      None, QApplication.UnicodeUTF8))

        self.mainLayout.addWidget(self.treeWidget)

        # overrides panel
        # TODO style for dock widgets
        self.overridesPanel = QDockWidget(self.centralwidget)
        op_stylesheet = self.overridesPanel.styleSheet()
        self.overridesPanel.setStyleSheet(op_stylesheet +
                                          "QDockWidget {border:1px solid darkgray;border-radius:2px;}" +
                                          "QDockWidget::title {text-align: center; /* align the text to the left */\
                                                              padding-left: 5px;\
                                                              border:1px solid rgb(80,80,80);\
                                                              border-radius:2px;\
                                                            }")

        self.overridesPanel.setMinimumSize(QSize(250, 41))
        self.overridesPanel.setWindowTitle(
            QApplication.translate("MainWindow", "Overrides", None, QApplication.UnicodeUTF8))
        self.overridesPanel.setFeatures(
            QDockWidget.DockWidgetFloatable | QDockWidget.DockWidgetMovable)
        self.overridesPanelContents = QWidget()
        self.overridesPanelContents.setLayout(QVBoxLayout())
        self.overridesPanelContents.setObjectName(_fromUtf8("overridesPanelContents"))
        self.overridesPanel.setWidget(self.overridesPanelContents)
        self.addDockWidget(Qt.DockWidgetArea(Qt.RightDockWidgetArea), self.overridesPanel)

    def setupActions(self):

        self.addExpressionAction = None
        self.removeExpressionAction = None
        self.checkExpressionAction = None
        self.applyShaderAction = None
        self.applyDisplacementAction = None
        self.removeShaderAction = None
        self.removeDisplacementAction = None

    def setupConnections(self):

        # tree selection -> overrides panel

        self.treeWidget.currentItemChanged.connect(self.populateOverridesPanel)
        self.treeWidget.currentItemChanged.connect(self.setConextMenuActions)
        self.treeWidget.itemChanged.connect(self.setTreeItemValues)
        self.treeWidget.setContextMenuPolicy(Qt.ActionsContextMenu)

        self.refreshSelectionButton.clicked.connect(self.refreshUI)

    def refreshUI(self, selection=[]):

        if not len(selection):
            selection = self.getSelected()

        self.treeWidget.clear()

        clearWidget(self.overridesPanelContents)

        if len(selection):
            usableNodes = []
            for n in _mc.ls(selection, dag=True, ap=True, shapes=True):
                if _mc.nodeType(n) in self.nodes:
                    usableNodes.append(n)
            self.currentSelection = usableNodes
            self.populateGraph()

    def populateGraph(self):
        for node in self.currentSelection:
            if _mc.nodeType(node) in self.nodes:
                self.addNodeToGraph(_pc.PyNode(node))

    def addNodeToGraph(self, node):

        # get the filepath and the object path from the node
        abcfile, startpoint = self.getAbcFilePath(node)

        if not cask.is_valid(abcfile):
                print "Not a valid Alembic file", abcfile
                return
        else:
            a = cask.Archive(abcfile)
            # get to the start point
            if startpoint not in ['/', '']:
                a = self.getObject(a.top, startpoint)

            abc_item = self.walktree(a.top, node)  # walk the graph
            AbcIcon = QIcon()
            AbcIcon.addPixmap(QPixmap("/sw/pkg/bbalembic/1.0.0/maya/2017/icons/abcLogo.png"))
            abc_item.setIcon(0, AbcIcon)

            top_item = QTreeWidgetItem()
            top_item.setText(0, node.nodeName())
            top_item.node = node
            top_item.fullPath = 'x'
            top_item.addChild(abc_item)

            # add the expression tree items

            expressionRootItem = QTreeWidgetItem()
            ExpressionIcon = QIcon()
            ExpressionIcon.addPixmap(
                self.treeWidget.style().standardPixmap(QStyle.SP_FileDialogDetailedView))
            expressionRootItem.setIcon(0, ExpressionIcon)

            expressionRootItem.setText(0, "Expressions")
            expressionRootItem.fullPath = 'x'
            expressionRootItem.type = 'expression_root'

            # get the expressions on the node currently

            self.updateExpressionTree(node, expressionRootItem)

            top_item.addChild(expressionRootItem)

            # add context menus
            self.treeWidget.addTopLevelItem(top_item)
            # force the top item to be expanded
            top_item.setExpanded(True)

    def updateExpressionTree(self, node, expressionRoot):
        # get the json attributes
        o_dict, s_dict, d_dict, ua_dict = self.getJSONData(node)
        patterns_list = {}
        # gather the patterns that are being used
        for key, values in o_dict.items():
            if key not in patterns_list and (key.find('/') == -1 or key.find('*') != -1):
                patterns_list[key] = {}
                patterns_list[key]['overrides'] = values
            elif key.find('/') == -1 or key.find('*') != -1:
                patterns_list[key]['overrides'] = values

        for key, values in ua_dict.items():
            if key not in patterns_list and (key.find('/') == -1 or key.find('*') != -1):
                patterns_list[key] = {}
                patterns_list[key]['userAttributes'] = values
            elif key.find('/') == -1 or key.find('*') != -1:
                patterns_list[key]['userAttributes'] = values

        for shdr, value in s_dict.items():
            for key in value:
                if key not in patterns_list and (key.find('/') == -1 or key.find('*') != -1):
                    patterns_list[key] = {}
                    patterns_list[key]['shader'] = shdr
                elif key.find('/') == -1 or key.find('*') != -1:
                    patterns_list[key]['shader'] = shdr

        for disp, value in d_dict.items():
            for key in value:
                if key not in patterns_list and (key.find('/') == -1 or key.find('*') != -1):
                    patterns_list[key] = {}
                    patterns_list[key]['displacement'] = disp
                elif key.find('/') == -1 or key.find('*') != -1:
                    patterns_list[key]['displacement'] = disp

        # now add the expressions to the expression tree
        old_children = expressionRoot.takeChildren()
        for expr in patterns_list:
            this_expr = self.addExpression(expressionRoot)
            this_expr.setText(0, expr)
            this_expr.fullPath = expr

            # add shaders
            if 'shader' in patterns_list[expr]:
                this_expr.setText(1, patterns_list[expr]['shader'])
            # add displacements
            if 'displacement' in patterns_list[expr]:
                this_expr.setText(2, patterns_list[expr]['displacement'])

            if 'overrides' in patterns_list[expr]:
                this_expr.setText(3, ','.join(patterns_list[expr]['overrides'].keys()))

            if 'userAttributes' in patterns_list[expr]:
                this_expr.setText(4, ','.join(patterns_list[expr]['userAttributes'].keys()))

    def getJSONData(self, node):

        overrides = {}
        userAttributes = {}
        shaderAssignation = {}
        displacementAssignation = {}

        if node.hasAttr('overrides') and node.overrides.get() != '':
            try:
                overrides = json.loads(node.overrides.get())
            except ValueError as E:
                pass
        if node.hasAttr('shaderAssignation') and node.shaderAssignation.get() != '':
            try:
                shaderAssignation = json.loads(node.shaderAssignation.get())
            except ValueError as E:
                pass
        if node.hasAttr('displacementAssignation') and node.displacementAssignation.get() != '':
            try:
                displacementAssignation = json.loads(node.displacementAssignation.get())
            except ValueError as E:
                pass
        if node.hasAttr('userAttributes') and node.userAttributes.get() != '':
            try:
                userAttributes = json.loads(node.userAttributes.get())
            except ValueError as E:
                pass

        return overrides, shaderAssignation, displacementAssignation, userAttributes

    def getAbcFilePath(self, node):
        abcFilePath = ''
        abcObjectPath = '/'

        # switch for each nodetype gpuceche first
        if node.nodeType() == 'gpuCache':
            abcFilePath = node.cacheFileName.get()
            abcObjectPath = node.cacheGeomPath.get().replace('|', '/')

        return str(abcFilePath), str(abcObjectPath)

    def setConextMenuActions(self, treeItem):
        # clear the current actions
        for action in self.treeWidget.actions():
            self.treeWidget.removeAction(action)

        if not treeItem:
            return

        # get the type of tree item
        if treeItem.type == 'expression_root':
            if not self.addExpressionAction:
                self.addExpressionAction = QAction(u'Add Expression', self)
                self.addExpressionAction.triggered.connect(self.addExpression)
            self.treeWidget.addAction(self.addExpressionAction)
            return
        elif treeItem.type == 'expression':
            if not self.removeExpressionAction:
                self.removeExpressionAction = QAction(u'Remove Expression', self)
                self.removeExpressionAction.triggered.connect(self.removeExpression)
            self.treeWidget.addAction(self.removeExpressionAction)
            if not self.checkExpressionAction:
                self.checkExpressionAction = QAction(u'Check Expression', self)
                self.checkExpressionAction.triggered.connect(self.checkExpression)
            self.treeWidget.addAction(self.checkExpressionAction)

        if not self.applyShaderAction:
            self.applyShaderAction = QAction(u'Apply Shader', self)
            self.applyShaderAction.triggered.connect(self.applyShader)

        self.treeWidget.addAction(self.applyShaderAction)

        if not self.removeShaderAction:
            self.removeShaderAction = QAction(u'Remove Shader', self)
            self.removeShaderAction.triggered.connect(self.removeShader)

        self.treeWidget.addAction(self.removeShaderAction)

        if not self.applyDisplacementAction:
            self.applyDisplacementAction = QAction(u'Apply Displacement', self)
            self.applyDisplacementAction.triggered.connect(self.applyDisplacement)

        self.treeWidget.addAction(self.applyDisplacementAction)

        if not self.removeDisplacementAction:
            self.removeDisplacementAction = QAction(u'Remove Displacement', self)
            self.removeDisplacementAction.triggered.connect(self.removeDisplacement)

        self.treeWidget.addAction(self.removeDisplacementAction)

    def applyShader(self, *args, **argv):
        treeItem = self.treeWidget.currentItem()
        node = self.getRootItem(treeItem).node
        shader = ShadersChooser.getShader(parent=self, node=node)
        if shader:

            # get the current value of the override attribute

            s_dict = self.getJSONData(node)[1]

            if shader not in s_dict:
                s_dict[shader] = []

            path = treeItem.fullPath
            # remove the path fram any other shaders
            keys = s_dict.keys()
            for k in keys:
                if path in s_dict[k]:
                    s_dict[k].pop(s_dict[k].index(path))
                    if len(s_dict[k]) == 0:
                        s_dict.pop(k, None)

            if path not in s_dict[shader]:
                s_dict[shader].append(path)

            # set the overrides attribute
            node.shaderAssignation.set(json.dumps(s_dict))

            treeItem.setText(1, shader)

    def applyDisplacement(self, *args, **argv):

        treeItem = self.treeWidget.currentItem()
        node = self.getRootItem(treeItem).node
        shader = DisplacementChooser.getShader(parent=self, node=node)
        if shader:

            # get the current value of the override attribute

            d_dict = self.getJSONData(node)[2]

            if shader not in d_dict:
                d_dict[shader] = []
            path = treeItem.fullPath

            # remove the path fram any other shaders
            keys = d_dict.keys()
            for k in keys:
                if path in d_dict[k]:
                    d_dict[k].pop(d_dict[k].index(path))
                    if len(d_dict[k]) == 0:
                        d_dict.pop(k, None)

            if treeItem.fullPath not in d_dict[shader]:
                d_dict[shader].append(path)

            # set the overrides attribute
            node.displacementAssignation.set(json.dumps(d_dict))

            treeItem.setText(2, shader)

    def removeShader(self, *args, **argv):
        treeItem = self.treeWidget.currentItem()
        path = treeItem.fullPath
        node = self.getRootItem(treeItem).node

        s_dict = self.getJSONData(node)[1]
        keys = s_dict.keys()
        for k in keys:
            if path in s_dict[k]:
                s_dict[k].pop(s_dict[k].index(path))
                if len(s_dict[k]) == 0:
                    s_dict.pop(k, None)

        node.shaderAssignation.set(json.dumps(s_dict))
        treeItem.setText(1, "")

    def removeDisplacement(self, *args, **argv):
        treeItem = self.treeWidget.currentItem()
        path = treeItem.fullPath
        node = self.getRootItem(treeItem).node

        d_dict = self.getJSONData(node)[2]
        keys = d_dict.keys()
        for k in keys:
            if path in d_dict[k]:
                d_dict[k].pop(d_dict[k].index(path))
                if len(d_dict[k]) == 0:
                    d_dict.pop(k, None)

        node.displacementAssignation.set(json.dumps(d_dict))
        treeItem.setText(2, "")

    def removeOverride(self, attrBox, *args, **argv):
        attr = attrBox.attr
        treeItem = self.treeWidget.currentItem()
        path = treeItem.fullPath
        node = self.getRootItem(treeItem).node

        o_dict = self.getJSONData(node)[0]
        if path in o_dict.keys():
            o_dict[path].pop(attr, None)
            if len(o_dict[path].keys()) == 0:
                o_dict.pop(path, None)

        node.overrides.set(json.dumps(o_dict))
        if path in o_dict:
            treeItem.setText(3, ','.join(o_dict[path].keys()))
        else:
            treeItem.setText(3, '')
        attrBox.deleteLater()

    def removeUserAttr(self, attrBox, *args, **argv):
        attr = attrBox.attr
        treeItem = self.treeWidget.currentItem()
        path = treeItem.fullPath
        node = self.getRootItem(treeItem).node

        ua_dict = self.getJSONData(node)[3]
        if path in ua_dict.keys():
            ua_dict[path].pop(attr, None)
            if len(ua_dict[path].keys()) == 0:
                ua_dict.pop(path, None)

        node.userAttributes.set(json.dumps(ua_dict))
        if path in ua_dict:
            treeItem.setText(4, ','.join(ua_dict[path].keys()))
        else:
            treeItem.setText(4, '')

        attrBox.deleteLater()

    def addExpression(self, treeItem=None, *args, **argv):

        if not treeItem:
            treeItem = self.treeWidget.currentItem()

        new_expression = QTreeWidgetItem()
        # new_expression.setFlags(editable|enabled)
        new_expression.fullPath = "#"
        new_expression.setText(0, new_expression.fullPath)
        new_expression.type = 'expression'

        # get this expression item
        treeItem.addChild(new_expression)
        treeItem.setExpanded(True)  # force the expression tree to be expanded

        return new_expression

    def checkExpression(self, *args, **argv):
        """TODO"""
        this_expr = self.treeWidget.currentItem()
        node = self.getRootItem(this_expr).node
        abcfile, startpoint = self.getAbcFilePath(node)  # get the filepath and the object path from the node

        # load dialog and show the paths that match the expression given

        dialog = ExpressionCheckerDialog(expression=str(this_expr.text(0)),
                                         abcfile=abcfile,
                                         startpoint=startpoint,
                                         parent=self)
        dialog.show()

    def setTreeItemValues(self, item, col):
        if item.type == 'expression':
            if col == 0:
                this_item = item
                item_parent = item.parent()
                newpath = str(item.text(col))
                oldpath = item.fullPath

                # Find and change the expression value in node attributes
                node = self.getRootItem(this_item).node
                if isinstance(node, str) or isinstance(node, unicode):
                    node = _pc.PyNode(node)

                o_dict, s_dict, d_dict, ua_dict = self.getJSONData(node)

                if oldpath in o_dict:
                    if newpath not in o_dict:
                        o_dict[newpath] = {}
                    o_dict[newpath] = dict(o_dict[newpath].items() + o_dict.pop(oldpath).items())

                    this_item.setText(3, ','.join(o_dict[newpath].keys()))
               
                node.overrides.set(json.dumps(o_dict))

                if oldpath in ua_dict:
                    if newpath not in ua_dict:
                        ua_dict[newpath] = {}
                    ua_dict[newpath] = dict(ua_dict[newpath].items() + ua_dict.pop(oldpath).items())
        
                    this_item.setText(4, ','.join(ua_dict[newpath].keys()))

                node.userAttributes.set(json.dumps(ua_dict))

                for shdr in s_dict.keys():
                    if newpath not in s_dict[shdr]:
                        s_dict[shdr] = [newpath if x == oldpath else x for x in s_dict[shdr]]
                   
                    if oldpath in s_dict[shdr]:
                        s_dict[shdr].pop(oldpath)
                   
                    # set the field in the tree
                    if newpath in s_dict[shdr]:
                        this_item.setText(1, shdr)

                    node.shaderAssignation.set(json.dumps(s_dict))
                    for disp in d_dict.keys():
                        if newpath not in d_dict[disp]:
                            d_dict[disp] = [newpath if x == oldpath else x for x in d_dict[disp]]
                        if oldpath in d_dict[disp]:
                            d_dict[disp].pop(oldpath)

                        # set the field in the tree
                        if newpath in d_dict[disp]:
                            this_item.setText(2, disp)

                node.displacementAssignation.set(json.dumps(d_dict))

                # Check if this pattern already exists in the expression tree
                # we need to combine the items together
                matchItems = []
                for i in range(item_parent.childCount()):
                    this_child = item_parent.child(i)
                    if i != item_parent.indexOfChild(this_item) and this_child.text(0) == newpath:
                        matchItems.append(this_child)

                for mi in matchItems:
                    item_parent.removeChild(mi)

                this_item.fullPath = newpath
                # self.n_pathBox.setText(newpath)
                self.populateOverridesPanel(this_item)

    def removeExpression(self, *args, **argv):

        # get selected expression
        this_expr = self.treeWidget.currentItem()
        node = self.getRootItem(this_expr).node
        path = this_expr.fullPath

        o_dict, s_dict, d_dict, ua_dict = self.getJSONData(node)

        if path in o_dict.keys():
            o_dict.pop(path, None)
        node.overrides.set(json.dumps(o_dict))

        if path in ua_dict.keys():
            ua_dict.pop(path, None)
        node.userAttributes.set(json.dumps(ua_dict))

        for shdr, paths in s_dict.items():
            if path in paths:
                s_dict[shdr].pop(s_dict[shdr].index(path))
            if not len(s_dict[shdr]):
                s_dict.pop(shdr)
        node.shaderAssignation.set(json.dumps(s_dict))

        for disp, paths in d_dict.items():
            if path in paths:
                d_dict[disp].pop(d_dict[disp].index(path))
            if not len(d_dict[disp]):
                d_dict.pop(disp)
        node.displacementAssignation.set(json.dumps(d_dict))

        root = this_expr.parent()
        this_expr_idx = root.indexOfChild(this_expr)
        root.takeChild(this_expr_idx)

    def setPattern(self):
        """Set the expression pattern to text"""
        text = self.n_pathBox.text()
        this_expr = self.treeWidget.currentItem()
        this_expr.setText(0,text) # FIXME check if pattern exists already/redraw the tree
        # self.updateExpressionTree(self.getRootItem(this_expr).node,this_expr.parent())
        # self.refreshUI()

    def walktree(self, iobject, node):
        """Walk the tree of nodes in the alembic file"""

        item = QTreeWidgetItem()
        item.setText(0, str(iobject.name))
        fullpath = iobject.path()
        # get if this item has a shader or displacment assigned
        o_dict, s_dict, d_dict, ua_dict = self.getJSONData(node)
        for s, v in s_dict.items():
            if fullpath in v:
                item.setText(1, s)
        for s, v in d_dict.items():
            if fullpath in v:
                item.setText(2, s)
        if fullpath in o_dict.keys():
                item.setText(3, ','.join(o_dict[fullpath].keys()))
        if fullpath in ua_dict.keys():
                item.setText(4, ','.join(ua_dict[fullpath].keys()))

        item.node = node
        item.fullPath = fullpath
        item.type = 'iobject'
        for child in iobject.children.values():
            print child
            this_treeItem = self.walktree(child, node)
            item.addChild(this_treeItem)

        return item

    def getObject(self, obj, targetPath):

        out_obj = None
        for c in obj.children.values():
            this_path = c.path()
            if this_path == targetPath:
                return c
            else:
                out_obj = self.getObject(c, targetPath)
                if out_obj:
                    return out_obj
      
        return None

    def populateOverridesPanel(self, treeItem):
        if not treeItem:
            return
        clearWidget(self.overridesPanelContents)

        self.n_pathBox = QLineEdit(treeItem.fullPath)

        if treeItem.type == 'expression':
            self.n_pathBox.editingFinished.connect(self.setPattern)
            # self.n_pathBox.setStyleSheet("QLineEdit {background-color:srgb(20,20,20)}")
        else:
            self.n_pathBox.setReadOnly(True)

        self.overridesPanelContents.layout().addWidget(self.n_pathBox)
        # get the current overrides for the selected object.

        scroll_box = QScrollArea(self.overridesPanelContents)
        scroll_boxPanel = QWidget(scroll_box)
        scroll_boxPanelLayout = QVBoxLayout()
        scroll_boxPanel.setLayout(scroll_boxPanelLayout)

        scroll_box.setWidget(scroll_boxPanel)
        scroll_box.setWidgetResizable(True)

        addOverridesButton = QPushButton("Add Override")
        addOverridesButton.clicked.connect(lambda: self.addOverride(treeItem))
        scroll_boxPanelLayout.addWidget(addOverridesButton)

        addUserAttrButton = QPushButton("Add User Attribute")
        addUserAttrButton.clicked.connect(lambda: self.addUserAttribute(treeItem))
        scroll_boxPanelLayout.addWidget(addUserAttrButton)

        self.overrides_box = AttrCollapseFrame("Overrides", self.overridesPanelContents)
        self.overrides_box.setExpanded()
        self.overrides_box.centreLayout.insertStretch(-1)
        # add overrides
        self.updateOverrides(treeItem)
        scroll_boxPanelLayout.addWidget(self.overrides_box)

        self.userAttributes_box = AttrCollapseFrame("User Attributes", self.overridesPanelContents)
        self.userAttributes_box.setExpanded()
        self.userAttributes_box.centreLayout.insertStretch(-1)
        # add user attributes
        self.updateUserAttributes(treeItem)
        scroll_boxPanelLayout.addWidget(self.userAttributes_box)

        scroll_boxPanelLayout.insertStretch(-1)
        self.overridesPanelContents.layout().addWidget(scroll_box)

    def getRootItem(self, treeItem):
        current_item = treeItem
        current_parent = treeItem.parent()
        while current_parent is not None:
            current_item = current_parent
            current_parent = current_item.parent()

        return current_item

    def addOverride(self, treeItem):

        overrides = OverrideChooser.getOverrides()

        node = self.getRootItem(treeItem).node

        # get the current value of the override attribute

        o_dict = self.getJSONData(node)[0]

        if not o_dict.has_key(treeItem.fullPath):
            o_dict[treeItem.fullPath] = {}

        for o in overrides:
            if o not in o_dict[treeItem.fullPath]:
                o_dict[treeItem.fullPath][o] = overrides[o]['default']

        # set the overrides attribute

        node.overrides.set(json.dumps(o_dict))

        # update the overrides panel for this item

        self.updateOverrides(treeItem)

        # update the overrides colum in the tree view
        treeItem.setText(3, ','.join(o_dict[treeItem.fullPath].keys()))

    def updateOverrides(self, treeItem):
        node = self.getRootItem(treeItem).node
        pattern = treeItem.fullPath

        clearWidget(self.overrides_box.centreLayout)

        o_dict = self.getJSONData(node)[0]

        if pattern in o_dict:
            theseAttrs = o_dict[pattern]

            for attr, value in theseAttrs.items():

                if attr == 'visibility':
                    thisAttrBox = VisibilityLabelWidget(attr)
                    thisAttrBox.node = node.fullPath()
                    thisAttrBox.blockSignals(True)
                    thisAttrBox.setValue(value)
                    thisAttrBox.blockSignals(False)
                    thisAttrBox.attr = attr
                    thisAttrBox.pattern = pattern
                    thisAttrBox.valueChanged.connect(self.setOverrideValue)
                    thisAttrBox.deleteAttr.connect(
                        functools.partial(self.removeOverride, thisAttrBox))
                    self.overrides_box.centreLayout.insertWidget(-2, thisAttrBox)
                elif self.allParams[attr]['type'] in ['INT', 'BYTE', 'UINT']:
                    thisAttrBox = IntLabelWidget(attr)
                    thisAttrBox.setValue(value)
                    thisAttrBox.node = node.fullPath()
                    thisAttrBox.attr = attr
                    thisAttrBox.pattern = pattern
                    thisAttrBox.valueChanged.connect(self.setOverrideValue)
                    thisAttrBox.deleteAttr.connect(
                        functools.partial(self.removeOverride, thisAttrBox))
                    self.overrides_box.centreLayout.insertWidget(-2, thisAttrBox)
                elif self.allParams[attr]['type'] in ['FLOAT']:
                    thisAttrBox = FloatLabelWidget(attr)
                    thisAttrBox.setValue(value)
                    thisAttrBox.node = node.fullPath()
                    thisAttrBox.attr = attr
                    thisAttrBox.pattern = pattern
                    thisAttrBox.valueChanged.connect(self.setOverrideValue)
                    thisAttrBox.deleteAttr.connect(
                        functools.partial(self.removeOverride, thisAttrBox))
                    self.overrides_box.centreLayout.insertWidget(-2, thisAttrBox)
                elif self.allParams[attr]['type'] in ['BOOL']:
                    thisAttrBox = BoolLabelWidget(attr)
                    thisAttrBox.setValue(value)
                    thisAttrBox.node = node.fullPath()
                    thisAttrBox.attr = attr
                    thisAttrBox.pattern = pattern
                    thisAttrBox.valueChanged.connect(self.setOverrideValue)
                    thisAttrBox.deleteAttr.connect(
                        functools.partial(self.removeOverride, thisAttrBox))
                    self.overrides_box.centreLayout.insertWidget(-2, thisAttrBox)
                elif self.allParams[attr]['type'] in ['ENUM']:
                    thisAttrBox = EnumLabelWidget(attr, options=getArnoldEnumOptions(attr))
                    thisAttrBox.setValue(value)
                    thisAttrBox.node = node.fullPath()
                    thisAttrBox.attr = attr
                    thisAttrBox.pattern = pattern
                    thisAttrBox.valueChanged.connect(self.setOverrideValue)
                    thisAttrBox.deleteAttr.connect(
                        functools.partial(self.removeOverride, thisAttrBox))
                    self.overrides_box.centreLayout.insertWidget(-2, thisAttrBox)

    def setOverrideValue(self, node, pattern, attr, value):

        if isinstance(node, str) or isinstance(node, unicode):
            node = _pc.PyNode(node)

        o_dict = self.getJSONData(node)[0]
        o_dict[pattern][attr] = value

        node.overrides.set(json.dumps(o_dict))

    def addUserAttribute(self, treeItem):

        userAttrType = UserAttrChooser.getAttr()

        node = self.getRootItem(treeItem).node

        # get the current value of the override attribute

        ua_dict = self.getJSONData(node)[3]

        if treeItem.fullPath not in ua_dict:
            ua_dict[treeItem.fullPath] = {}

        prefix = 'user%sAttr' % ''.join(t.title() for t in userAttrType.split())
        n = 1
        thisAttrName = prefix + str(n)
        while thisAttrName in ua_dict[treeItem.fullPath]:
            n += 1
            thisAttrName = prefix + str(n)

        if userAttrType == 'INT':
            ua_dict[treeItem.fullPath][thisAttrName] = 0
        if userAttrType == 'FLOAT':
            ua_dict[treeItem.fullPath][thisAttrName] = 0.0
        if userAttrType == 'BOOL':
            ua_dict[treeItem.fullPath][thisAttrName] = False
        if userAttrType == 'STRING':
            ua_dict[treeItem.fullPath][thisAttrName] = ''
        if userAttrType == 'STRING ARRAY':
            ua_dict[treeItem.fullPath][thisAttrName] = ['']

        node.userAttributes.set(json.dumps(ua_dict))

        # update the overrides panel for this item

        self.updateUserAttributes(treeItem)

        # update the overrides colum in the tree view
        treeItem.setText(4, ','.join(ua_dict[treeItem.fullPath].keys()))

    def updateUserAttributes(self, treeItem):
        node = self.getRootItem(treeItem).node
        pattern = treeItem.fullPath

        clearWidget(self.userAttributes_box.centreLayout)

        ua_dict = self.getJSONData(node)[3]

        if pattern in ua_dict:
            theseAttrs = ua_dict[pattern]

            for attr, value in theseAttrs.items():

                if type(value) in [int]:
                    thisAttrBox = UserIntAttrBox()
                    thisAttrBox.setAttrName(attr)
                    thisAttrBox.setValue(value)
                    thisAttrBox.node = node.fullPath()
                    thisAttrBox.attr = attr
                    thisAttrBox.pattern = pattern
                    thisAttrBox.valueChanged.connect(self.setUserAttrValue)
                    thisAttrBox.attrChanged.connect(self.setUserAttrName)
                    thisAttrBox.deleteAttr.connect(
                        functools.partial(self.removeUserAttr, thisAttrBox))
                    self.userAttributes_box.centreLayout.insertWidget(-2, thisAttrBox)
                elif type(value) in [float]:
                    thisAttrBox = UserFloatAttrBox(attr)
                    thisAttrBox.setAttrName(attr)
                    thisAttrBox.setValue(value)
                    thisAttrBox.node = node.fullPath()
                    thisAttrBox.attr = attr
                    thisAttrBox.pattern = pattern
                    thisAttrBox.valueChanged.connect(self.setUserAttrValue)
                    thisAttrBox.attrChanged.connect(self.setUserAttrName)
                    thisAttrBox.deleteAttr.connect(
                        functools.partial(self.removeUserAttr, thisAttrBox))
                    self.userAttributes_box.centreLayout.insertWidget(-2, thisAttrBox)
                elif type(value) in [bool]:
                    thisAttrBox = UserBoolAttrBox(attr)
                    thisAttrBox.setAttrName(attr)
                    thisAttrBox.setValue(value)
                    thisAttrBox.node = node.fullPath()
                    thisAttrBox.attr = attr
                    thisAttrBox.pattern = pattern
                    thisAttrBox.valueChanged.connect(self.setUserAttrValue)
                    thisAttrBox.attrChanged.connect(self.setUserAttrName)
                    thisAttrBox.deleteAttr.connect(
                        functools.partial(self.removeUserAttr, thisAttrBox))
                    self.userAttributes_box.centreLayout.insertWidget(-2, thisAttrBox)
                elif type(value) in [str, unicode]:
                    thisAttrBox = UserStringAttrBox(attr)
                    thisAttrBox.setAttrName(attr)
                    thisAttrBox.setValue(value)
                    thisAttrBox.node = node.fullPath()
                    thisAttrBox.attr = attr
                    thisAttrBox.pattern = pattern
                    thisAttrBox.valueChanged.connect(self.setUserAttrValue)
                    thisAttrBox.attrChanged.connect(self.setUserAttrName)
                    thisAttrBox.deleteAttr.connect(
                        functools.partial(self.removeUserAttr, thisAttrBox))
                    self.userAttributes_box.centreLayout.insertWidget(-2, thisAttrBox)
                elif type(value) in [list, tuple]:
                    thisAttrBox = UserStringArrayAttrBox(attr)
                    thisAttrBox.setAttrName(attr)
                    thisAttrBox.setValue(value)
                    thisAttrBox.node = node.fullPath()
                    thisAttrBox.attr = attr
                    thisAttrBox.pattern = pattern
                    thisAttrBox.valueChanged.connect(self.setUserAttrValue)
                    thisAttrBox.attrChanged.connect(self.setUserAttrName)
                    thisAttrBox.deleteAttr.connect(
                        functools.partial(self.removeUserAttr, thisAttrBox))
                    self.userAttributes_box.centreLayout.insertWidget(-2, thisAttrBox)

    def setUserAttrValue(self, node, pattern, attr, value):

        if isinstance(node, str) or isinstance(node, unicode):
            node = _pc.PyNode(node)

        ua_dict = self.getJSONData(node)[3]
        ua_dict[pattern][attr] = value

        node.userAttributes.set(json.dumps(ua_dict))

    def setUserAttrName(self, node, pattern, oldname, newname):

        if isinstance(node, str) or isinstance(node, unicode):
            node = _pc.PyNode(node)

        ua_dict = self.getJSONData(node)[3]

        ua_dict[pattern][newname] = ua_dict[pattern].pop(oldname)

        node.userAttributes.set(json.dumps(ua_dict))
         
        treeItem = self.treeWidget.currentItem()
        treeItem.setText(4, ','.join(ua_dict[pattern].keys()))

    # Signals

    def getSelected(self):
        nameList = _mc.ls(sl=True)
        nameList = [str(x) for x in nameList]
        return nameList

    def selectionChanged(self, *args):
        # if not self.active:return
        added = []
        removed = []
        all = []
        old = self.currentSelection
        self.currentSelection = self.getSelected()
        for element in old:
            if element not in self.currentSelection:
                removed.append(element)
             
        for element in self.currentSelection:
            if element not in old:
                added.append(element)
        self.selectedNode.emit(self.currentSelection, added, removed)

    def closeEvent(self, e):
        e.accept()


if __name__ == '__main__':
    # app = QApplication([])

    w = AlembicEditorWindow(mayaMainWindow)
     
    w.show()
    # app.exec_()
