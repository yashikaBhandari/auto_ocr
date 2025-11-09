"""GPU Manager for optional CUDA/OpenCV GPU acceleration.

Handles GPU detection and provides unified interface for CPU/GPU operations.
"""
import cv2
import numpy as np
from typing import Optional, Any
from .logging import get_logger

logger = get_logger("gpu_manager")


class GPUManager:
    """Manages GPU acceleration for OpenCV operations."""

    def __init__(self):
        self.has_cuda = self._check_cuda()
        self.has_tensorrt = self._check_tensorrt()

        if self.has_cuda:
            logger.info(f"CUDA enabled: {cv2.cuda.getCudaEnabledDeviceCount()} device(s) found")
        else:
            logger.info("CUDA not available, using CPU")

    def _check_cuda(self) -> bool:
        """Check if CUDA is available in OpenCV."""
        try:
            return cv2.cuda.getCudaEnabledDeviceCount() > 0
        except AttributeError:
            return False

    def _check_tensorrt(self) -> bool:
        """Check if TensorRT is available."""
        try:
            import tensorrt  # noqa: F401
            return True
        except ImportError:
            return False

    def allocate_image(self, image: np.ndarray):
        """Upload image to GPU memory if available.

        Args:
            image: numpy array (CPU memory)

        Returns:
            GpuMat if CUDA available, otherwise original numpy array
        """
        if self.has_cuda:
            gpu_mat = cv2.cuda_GpuMat()
            gpu_mat.upload(image)
            return gpu_mat
        return image

    def download_image(self, gpu_image) -> np.ndarray:
        """Download image from GPU to CPU.

        Args:
            gpu_image: GpuMat or numpy array

        Returns:
            numpy array
        """
        if self.has_cuda and isinstance(gpu_image, cv2.cuda_GpuMat):
            return gpu_image.download()
        return gpu_image

    def gaussian_blur(self, image: np.ndarray, ksize: tuple, sigma: float) -> np.ndarray:
        """Apply Gaussian blur with GPU acceleration if available."""
        if self.has_cuda:
            gpu_img = self.allocate_image(image)
            gpu_filter = cv2.cuda.createGaussianFilter(
                image.dtype, image.dtype, ksize, sigma
            )
            gpu_result = gpu_filter.apply(gpu_img)
            return self.download_image(gpu_result)
        return cv2.GaussianBlur(image, ksize, sigma)

    def bilateral_filter(self, image: np.ndarray, d: int, sigma_color: float,
                        sigma_space: float) -> np.ndarray:
        """Apply bilateral filter with GPU acceleration if available."""
        if self.has_cuda:
            gpu_img = self.allocate_image(image)
            gpu_filter = cv2.cuda.createBilateralFilter(
                image.dtype, d, sigma_color, sigma_space
            )
            gpu_result = gpu_filter.apply(gpu_img)
            return self.download_image(gpu_result)
        return cv2.bilateralFilter(image, d, sigma_color, sigma_space)

    def canny(self, image: np.ndarray, threshold1: float, threshold2: float) -> np.ndarray:
        """Apply Canny edge detection with GPU acceleration if available."""
        if self.has_cuda:
            gpu_img = self.allocate_image(image)
            gpu_detector = cv2.cuda.createCannyEdgeDetector(threshold1, threshold2)
            gpu_result = gpu_detector.detect(gpu_img)
            return self.download_image(gpu_result)
        return cv2.Canny(image, threshold1, threshold2)

    def median_blur(self, image: np.ndarray, ksize: int) -> np.ndarray:
        """Apply median blur (note: GPU version may not be available in all builds)."""
        # Median blur doesn't have good GPU support in OpenCV
        # Fall back to CPU even if CUDA available
        return cv2.medianBlur(image, ksize)

    def resize(self, image: np.ndarray, dsize: tuple, interpolation=cv2.INTER_LINEAR) -> np.ndarray:
        """Resize image with GPU acceleration if available."""
        if self.has_cuda:
            gpu_img = self.allocate_image(image)
            gpu_result = cv2.cuda.resize(gpu_img, dsize, interpolation=interpolation)
            return self.download_image(gpu_result)
        return cv2.resize(image, dsize, interpolation=interpolation)


# Global GPU manager instance
_gpu_manager: Optional[GPUManager] = None


def get_gpu_manager(force_cpu: bool = False) -> GPUManager:
    """Get global GPU manager instance.

    Args:
        force_cpu: If True, disable GPU even if available

    Returns:
        GPUManager instance
    """
    global _gpu_manager
    if _gpu_manager is None:
        _gpu_manager = GPUManager()

    # Override GPU settings if forced to CPU
    if force_cpu and _gpu_manager.has_cuda:
        _gpu_manager.has_cuda = False
        logger.info("GPU forced to disabled via force_cpu=True")

    return _gpu_manager
