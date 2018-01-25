from __future__ import absolute_import, division, print_function

from qtpy.QtCore import Qt
from qtpy import QtGui
from qtpy.QtWidgets import (
    QDialog, QApplication, QPushButton,
    QLabel, QWidget, QHBoxLayout, QVBoxLayout, QLineEdit
)

# TODO: In the future, it might be nice to be able to work across data_collection elements

class SelectArithmetic(QDialog):
    def __init__(self, data, data_collection, parent=None):
        super(SelectArithmetic,self).__init__(parent)

        # Get the data_components (e.g., FLUX, DQ, ERROR etc)
        # Using list comprehension to keep the order of the component_ids
        self.data_components = [str(x).strip() for x in data.component_ids() if not x in data.coordinate_components]

        self.setWindowFlags(self.windowFlags() | Qt.Tool)
        self.title = "Arithmetic Calculation"
        self.data = data
        self.data_collection = data_collection
        self.parent = parent

        self.currentAxes = None
        self.currentKernel = None

        self.createUI()

    def createUI(self):
        """
        Create the popup box with the calculation input area and buttons.

        :return:
        """
        boldFont = QtGui.QFont()
        boldFont.setBold(True)

        # Create calculation label and input box
        self.calculation_label = QLabel("Calculation:")
        self.calculation_label.setFixedWidth(100)
        self.calculation_label.setAlignment((Qt.AlignRight | Qt.AlignTop))
        self.calculation_label.setFont(boldFont)

        self.calculation_text = QLineEdit()
        self.calculation_text.setMinimumWidth(200)
        self.calculation_text.setAlignment((Qt.AlignLeft | Qt.AlignTop))

        hbl1 = QHBoxLayout()
        hbl1.addWidget(self.calculation_label)
        hbl1.addWidget(self.calculation_text)

        # Create calculation label and input box
        self.error_label = QLabel("")
        self.error_label.setFixedWidth(100)

        self.error_label_text = QLabel("")
        self.error_label_text.setMinimumWidth(200)
        self.error_label_text.setAlignment((Qt.AlignLeft | Qt.AlignTop))

        hbl_error = QHBoxLayout()
        hbl_error.addWidget(self.error_label)
        hbl_error.addWidget(self.error_label_text)

        # Show the available data
        self.data_available_text_label = QLabel("Data available: ")
        self.data_available_text_label.setFixedWidth(100)
        self.data_available_text_label.setAlignment((Qt.AlignRight | Qt.AlignTop))
        self.data_available_text_label.setFont(boldFont)

        self.data_available_label = QLabel(', '.join(self.data_components))
        self.data_available_label.setMinimumWidth(200)
        self.data_available_label.setAlignment((Qt.AlignLeft | Qt.AlignTop))

        hbl2 = QHBoxLayout()
        hbl2.addWidget(self.data_available_text_label)
        hbl2.addWidget(self.data_available_label)

        # Show the examples
        self.example_text_label = QLabel("Examples: ")
        self.example_text_label.setFixedWidth(100)
        self.example_text_label.setAlignment((Qt.AlignRight | Qt.AlignTop))
        self.example_text_label.setFont(boldFont)

        examples = """Assuming we have data available called FLUX and ERROR:

        - Subtract 1000 from {0}:  {0}new = {0} - 1000
        - Double the FLUX:  {0}new = {0} * 2
        - Scale FLUX between 0 and 1:  {0}norm = ({0} - min({0})) - (max({0})-min({0}))
        - Signal to noise: SNR = {0} / {1}
        - Masking: {0}new = {0} * ({1} < 0.1*mean({1}))
        """.format(self.data_components[0], self.data_components[1])

        self.examples_label = QLabel(examples)
        self.examples_label.setMinimumWidth(200)
        self.examples_label.setAlignment((Qt.AlignLeft | Qt.AlignTop))

        hbl_examples = QHBoxLayout()
        hbl_examples.addWidget(self.example_text_label)
        hbl_examples.addWidget(self.examples_label)

        # Create Calculate and Cancel buttons
        self.calculateButton = QPushButton("Calculate")
        self.calculateButton.clicked.connect(self.calculate_callback)
        self.calculateButton.setDefault(True)

        self.cancelButton = QPushButton("Cancel")
        self.cancelButton.clicked.connect(self.cancel_callback)

        hbl5 = QHBoxLayout()
        hbl5.addStretch(1)
        hbl5.addWidget(self.cancelButton)
        hbl5.addWidget(self.calculateButton)

        # Add calculation and buttons to popup box
        vbl = QVBoxLayout()
        vbl.addLayout(hbl1)
        vbl.addLayout(hbl_error)
        vbl.addLayout(hbl2)
        vbl.addLayout(hbl_examples)
        vbl.addLayout(hbl5)

        self.setLayout(vbl)
        self.setMaximumWidth(700)
        self.show()

    def calculate_callback(self):
        """
        Callback for when they hit calculate
        :return:
        """

        # Create the interpreter
        from asteval import Interpreter
        aeval = Interpreter()

        # Grab the calculation from the text box which the user wants to do
        calculation = str(self.calculation_text.text())

        lhs = calculation.split('=')[0].strip()

        # Use the package asteval to do the calculation, we are going to
        # assume here that the lhs of the equals sign is going to be the output named variable

        try:
            if lhs in self.data_components:
                raise KeyError('{} is already in the data components, use a different variable on the left hand side.'.format(lhs))

            # Pull in the required data and run the calculation
            for dc in self.data_components:
                if dc in calculation:
                    aeval.symtable[dc] = self.data[dc]
            aeval(calculation)

            # Pull out the output data and add to the proper drop-downs
            out_data = aeval.symtable[lhs]
            self.data.add_component(out_data, lhs)

            # Add the new data to the list of available data for arithemitic operations
            self.data_components.append(lhs)

            self.close()

        except KeyError as e:
            self.calculation_text.setStyleSheet("background-color: rgba(255, 0, 0, 128);")

            # Display the error in the Qt popup
            if aeval.error_msg:
                self.error_label_text.setText('{}'.format(aeval.error_msg))
            else:
                self.error_label_text.setText('{}'.format(e))

            self.error_label_text.setStyleSheet("color: rgba(255, 0, 0, 128)")

    def cancel_callback(self, caller=0):
        """
        Cancel callback when the person hits the cancel button

        :param caller:
        :return:
        """
        self.close()
