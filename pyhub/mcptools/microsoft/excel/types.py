from xlwings.constants import CellType, ConsolidationFunction, HAlign, VAlign

from pyhub.mcptools.core.types import NOT_SPECIFIED, PyHubIntegerChoices, PyHubTextChoices


class ExcelExpandMode(PyHubTextChoices):
    TABLE = "table", "Expand both right and down"
    RIGHT = "right", "Expand to the right"
    DOWN = "down", "Expand downward"


class ExcelGetValueType(PyHubTextChoices):
    VALUES = "values"
    FORMULA2 = "formula2"

    @classmethod
    def get_none_value(cls):
        return NOT_SPECIFIED


class ExcelChartType(PyHubTextChoices):
    THREE_D_AREA = "3d_area", "3D Area"
    THREE_D_AREA_STACKED = "3d_area_stacked", "3D Area Stacked"
    THREE_D_AREA_STACKED_100 = "3d_area_stacked_100", "3D Area Stacked 100"
    THREE_D_BAR_CLUSTERED = "3d_bar_clustered", "3D Bar Clustered"
    THREE_D_BAR_STACKED = "3d_bar_stacked", "3D Bar Stacked"
    THREE_D_BAR_STACKED_100 = "3d_bar_stacked_100", "3D Bar Stacked 100"
    THREE_D_COLUMN = "3d_column", "3D Column"
    THREE_D_COLUMN_CLUSTERED = "3d_column_clustered", "3D Column Clustered"
    THREE_D_COLUMN_STACKED = "3d_column_stacked", "3D Column Stacked"
    THREE_D_COLUMN_STACKED_100 = "3d_column_stacked_100", "3D Column Stacked 100"
    THREE_D_LINE = "3d_line", "3D Line"
    THREE_D_PIE = "3d_pie", "3D Pie"
    THREE_D_PIE_EXPLODED = "3d_pie_exploded", "3D Pie Exploded"
    AREA = "area", "Area"
    AREA_STACKED = "area_stacked", "Area Stacked"
    AREA_STACKED_100 = "area_stacked_100", "Area Stacked 100"
    BAR_CLUSTERED = "bar_clustered", "Bar Clustered"
    BAR_OF_PIE = "bar_of_pie", "Bar of Pie"
    BAR_STACKED = "bar_stacked", "Bar Stacked"
    BAR_STACKED_100 = "bar_stacked_100", "Bar Stacked 100"
    BUBBLE = "bubble", "Bubble"
    BUBBLE_3D_EFFECT = "bubble_3d_effect", "Bubble 3D Effect"
    COLUMN_CLUSTERED = "column_clustered", "Column Clustered"
    COLUMN_STACKED = "column_stacked", "Column Stacked"
    COLUMN_STACKED_100 = "column_stacked_100", "Column Stacked 100"
    COMBINATION = "combination", "Combination"
    CONE_BAR_CLUSTERED = "cone_bar_clustered", "Cone Bar Clustered"
    CONE_BAR_STACKED = "cone_bar_stacked", "Cone Bar Stacked"
    CONE_BAR_STACKED_100 = "cone_bar_stacked_100", "Cone Bar Stacked 100"
    CONE_COL = "cone_col", "Cone Column"
    CONE_COL_CLUSTERED = "cone_col_clustered", "Cone Column Clustered"
    CONE_COL_STACKED = "cone_col_stacked", "Cone Column Stacked"
    CONE_COL_STACKED_100 = "cone_col_stacked_100", "Cone Column Stacked 100"
    CYLINDER_BAR_CLUSTERED = "cylinder_bar_clustered", "Cylinder Bar Clustered"
    CYLINDER_BAR_STACKED = "cylinder_bar_stacked", "Cylinder Bar Stacked"
    CYLINDER_BAR_STACKED_100 = "cylinder_bar_stacked_100", "Cylinder Bar Stacked 100"
    CYLINDER_COL = "cylinder_col", "Cylinder Column"
    CYLINDER_COL_CLUSTERED = "cylinder_col_clustered", "Cylinder Column Clustered"
    CYLINDER_COL_STACKED = "cylinder_col_stacked", "Cylinder Column Stacked"
    CYLINDER_COL_STACKED_100 = "cylinder_col_stacked_100", "Cylinder Column Stacked 100"
    DOUGHNUT = "doughnut", "Doughnut"
    DOUGHNUT_EXPLODED = "doughnut_exploded", "Doughnut Exploded"
    LINE = "line", "Line"
    LINE_MARKERS = "line_markers", "Line Markers"
    LINE_MARKERS_STACKED = "line_markers_stacked", "Line Markers Stacked"
    LINE_MARKERS_STACKED_100 = "line_markers_stacked_100", "Line Markers Stacked 100"
    LINE_STACKED = "line_stacked", "Line Stacked"
    LINE_STACKED_100 = "line_stacked_100", "Line Stacked 100"
    PIE = "pie", "Pie"
    PIE_EXPLODED = "pie_exploded", "Pie Exploded"
    PIE_OF_PIE = "pie_of_pie", "Pie of Pie"
    PYRAMID_BAR_CLUSTERED = "pyramid_bar_clustered", "Pyramid Bar Clustered"
    PYRAMID_BAR_STACKED = "pyramid_bar_stacked", "Pyramid Bar Stacked"
    PYRAMID_BAR_STACKED_100 = "pyramid_bar_stacked_100", "Pyramid Bar Stacked 100"
    PYRAMID_COL = "pyramid_col", "Pyramid Column"
    PYRAMID_COL_CLUSTERED = "pyramid_col_clustered", "Pyramid Column Clustered"
    PYRAMID_COL_STACKED = "pyramid_col_stacked", "Pyramid Column Stacked"
    PYRAMID_COL_STACKED_100 = "pyramid_col_stacked_100", "Pyramid Column Stacked 100"
    RADAR = "radar", "Radar"
    RADAR_FILLED = "radar_filled", "Radar Filled"
    RADAR_MARKERS = "radar_markers", "Radar Markers"
    STOCK_HLC = "stock_hlc", "Stock HLC"
    STOCK_OHLC = "stock_ohlc", "Stock OHLC"
    STOCK_VHLC = "stock_vhlc", "Stock VHLC"
    STOCK_VOHLC = "stock_vohlc", "Stock VOHLC"
    SURFACE = "surface", "Surface"
    SURFACE_TOP_VIEW = "surface_top_view", "Surface Top View"
    SURFACE_TOP_VIEW_WIREFRAME = "surface_top_view_wireframe", "Surface Top View Wireframe"
    SURFACE_WIREFRAME = "surface_wireframe", "Surface Wireframe"
    XY_SCATTER = "xy_scatter", "XY Scatter"
    XY_SCATTER_LINES = "xy_scatter_lines", "XY Scatter Lines"
    XY_SCATTER_LINES_NO_MARKERS = "xy_scatter_lines_no_markers", "XY Scatter Lines No Markers"
    XY_SCATTER_SMOOTH = "xy_scatter_smooth", "XY Scatter Smooth"
    XY_SCATTER_SMOOTH_NO_MARKERS = "xy_scatter_smooth_no_markers", "XY Scatter Smooth No Markers"


class ExcelHorizontalAlignment(PyHubIntegerChoices):
    GENERAL = HAlign.xlHAlignGeneral, "General"
    LEFT = HAlign.xlHAlignLeft, "Left"
    CENTER = HAlign.xlHAlignCenter, "Center"
    RIGHT = HAlign.xlHAlignRight, "Right"
    FILL = HAlign.xlHAlignFill, "Fill"
    JUSTIFY = HAlign.xlHAlignJustify, "Justify"
    CENTER_ACROSS_SELECTION = HAlign.xlHAlignCenterAcrossSelection, "Center Across Selection"
    DISTRIBUTED = HAlign.xlHAlignDistributed, "Distributed"


class ExcelVerticalAlignment(PyHubIntegerChoices):
    TOP = VAlign.xlVAlignTop, "Top"
    CENTER = VAlign.xlVAlignCenter, "Center"
    BOTTOM = VAlign.xlVAlignBottom, "Bottom"
    JUSTIFY = VAlign.xlVAlignJustify, "Justify"
    DISTRIBUTED = VAlign.xlVAlignDistributed, "Distributed"


class ExcelCellType(PyHubIntegerChoices):
    ALL_FORMAT_CONDITIONS = CellType.xlCellTypeAllFormatConditions, "All Format Conditions"
    ALL_VALIDATION = CellType.xlCellTypeAllValidation, "All Validations"
    BLANKS = CellType.xlCellTypeBlanks, "Blank Cells"
    COMMENTS = CellType.xlCellTypeComments, "Cells with Comments"
    CONSTANTS = CellType.xlCellTypeConstants, "Constant Values"
    FORMULAS = CellType.xlCellTypeFormulas, "Formula Cells"
    LAST_CELL = CellType.xlCellTypeLastCell, "Last Used Cell"
    SAME_FORMAT_CONDITIONS = CellType.xlCellTypeSameFormatConditions, "Same Format Conditions"
    SAME_VALIDATION = CellType.xlCellTypeSameValidation, "Same Validation Rules"
    VISIBLE = CellType.xlCellTypeVisible, "Visible Cells"


class ExcelAggregationType(PyHubIntegerChoices):
    SUM = ConsolidationFunction.xlSum, "Sum"
    COUNT = ConsolidationFunction.xlCount, "Count"
    COUNT_NUMS = ConsolidationFunction.xlCountNums, "Count Numbers"
    AVERAGE = ConsolidationFunction.xlAverage, "Average"
    MAX = ConsolidationFunction.xlMax, "Max"
    MIN = ConsolidationFunction.xlMin, "Min"
    PRODUCT = ConsolidationFunction.xlProduct, "Product"
    STDEV = ConsolidationFunction.xlStDev, "Standard Deviation"
    STDEVP = ConsolidationFunction.xlStDevP, "Standard Deviation Population"
    VAR = ConsolidationFunction.xlVar, "Variance"
    VARP = ConsolidationFunction.xlVarP, "Variance Population"
    UNKNOWN = ConsolidationFunction.xlUnknown, "Unknown"
