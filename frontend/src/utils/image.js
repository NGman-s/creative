/**
 * Camera and Image Processing Utilities
 */

/**
 * Capture an image from camera or choose from gallery
 * @param {Object} options
 * @returns {Promise<string>} - temp file path of the chosen image
 */
export const chooseImage = (sourceType = ['camera', 'album']) => {
  return new Promise((resolve, reject) => {
    uni.chooseImage({
      count: 1,
      sizeType: ['compressed'],
      sourceType: sourceType,
      success: (res) => {
        resolve(res.tempFilePaths[0]);
      },
      fail: (err) => {
        reject(err);
      }
    });
  });
};

/**
 * Compress an image to reduce size while maintaining acceptable quality for AI analysis
 * @param {string} src - source image path
 * @param {number} quality - compression quality (0-100)
 * @returns {Promise<string>} - temp file path of the compressed image
 */
export const compressImage = (src, quality = 60) => {
  return new Promise((resolve, reject) => {
    // Check if uni.compressImage is supported (e.g., in H5 it might not be available)
    if (!uni.compressImage) {
      console.warn('uni.compressImage is not supported on this platform. Skipping compression.');
      resolve(src);
      return;
    }

    uni.compressImage({
      src: src,
      quality: quality,
      success: (res) => {
        resolve(res.tempFilePath);
      },
      fail: (err) => {
        // If compression fails, we might still want to proceed with the original image
        console.warn('Compression failed, using original image', err);
        resolve(src);
      }
    });
  });
};

export default {
  chooseImage,
  compressImage
};
