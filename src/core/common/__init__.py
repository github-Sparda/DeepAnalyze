"""DeepAnalyze 核心公共工具模块.

提供跨模块共享的基础工具函数和类.
"""

from .file_utils import ensure_dir, load_json, save_json, load_text, save_text, hash_file
from .json_utils import (
    extract_json_candidates,
    safe_json_load,
    safe_json_any,
    load_json_if_exists,
)
from .error_utils import (
    safe_execute,
    safe_convert_to_float,
    safe_convert_to_int,
    extract_hypothesis_id,
    find_nearest_centroid,
    detect_time_column,
    normalize_output_dir,
    retry_with_backoff,
    handle_error_with_context,
)
from .viz_utils import (
    create_basic_plot_setup,
    save_plot_and_close,
)
from .constants import (
    ANALYTICS_TOOLKIT_MODULES,
    MODEL_OUTPUT_FILES,
    STATS_OUTPUT_FILES,
    HYPOTHESIS_TYPE_MAP,
    METHOD_FAMILY_KEYWORDS,
)
from .weight_utils import (
    adjust_weights_by_p_value,
    adjust_weights_by_auc,
    adjust_weights_by_correlation,
    adjust_weights_by_metric,
)
from .context_managers import (
    error_handling_context,
    safe_execution_context,
    file_operation_context,
)
from .collab_utils import with_error_handling

__all__ = [
    # file_utils
    "ensure_dir",
    "load_json",
    "save_json",
    "load_text",
    "save_text",
    "hash_file",
    # json_utils
    "extract_json_candidates",
    "safe_json_load",
    "safe_json_any",
    "load_json_if_exists",
    # error_utils
    "safe_execute",
    "safe_convert_to_float",
    "safe_convert_to_int",
    "extract_hypothesis_id",
    "find_nearest_centroid",
    "detect_time_column",
    "normalize_output_dir",
    "retry_with_backoff",
    "handle_error_with_context",
    "error_handler_decorator",
    # viz_utils
    "create_basic_plot_setup",
    "save_plot_and_close",
    # constants
    "ANALYTICS_TOOLKIT_MODULES",
    "MODEL_OUTPUT_FILES",
    "STATS_OUTPUT_FILES",
    "HYPOTHESIS_TYPE_MAP",
    "METHOD_FAMILY_KEYWORDS",
    # weight_utils
    "adjust_weights_by_p_value",
    "adjust_weights_by_auc",
    "adjust_weights_by_correlation",
    "adjust_weights_by_metric",
    # context_managers
    "error_handling_context",
    "safe_execution_context",
    "file_operation_context",
    # collab_utils
    "with_error_handling",
]
