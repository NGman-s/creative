/**
 * Native Permission Handling Utility for Uni-app
 * Focuses on Camera and Gallery permissions for Android and iOS
 */

export const checkCameraPermission = () => {
  return new Promise((resolve, reject) => {
    // #ifdef APP-PLUS
    if (uni.getSystemInfoSync().platform === 'ios') {
      const AVCaptureDevice = plus.ios.importClass('AVCaptureDevice');
      const authStatus = AVCaptureDevice.authorizationStatusForMediaType('vide');
      if (authStatus === 3) {
        resolve(true);
      } else {
        reject(new Error('iOS相机权限被拒绝'));
      }
    } else {
      plus.android.requestPermissions(['android.permission.CAMERA'], (e) => {
        if (e.granted.length > 0) {
          resolve(true);
        } else {
          reject(new Error('Android相机权限被拒绝'));
        }
      }, (err) => {
        reject(err);
      });
    }
    // #endif

    // #ifndef APP-PLUS
    // H5 or MP handles permissions via standard browser prompts
    resolve(true);
    // #endif
  });
};

export const checkGalleryPermission = () => {
  return new Promise((resolve, reject) => {
    // #ifdef APP-PLUS
    if (uni.getSystemInfoSync().platform === 'ios') {
      const PHPhotoLibrary = plus.ios.importClass('PHPhotoLibrary');
      const authStatus = PHPhotoLibrary.authorizationStatus();
      if (authStatus === 3) {
        resolve(true);
      } else {
        reject(new Error('iOS相册权限被拒绝'));
      }
    } else {
      plus.android.requestPermissions(['android.permission.READ_EXTERNAL_STORAGE'], (e) => {
        if (e.granted.length > 0) {
          resolve(true);
        } else {
          reject(new Error('Android存储权限被拒绝'));
        }
      }, (err) => {
        reject(err);
      });
    }
    // #endif

    // #ifndef APP-PLUS
    resolve(true);
    // #endif
  });
};

export default {
  checkCameraPermission,
  checkGalleryPermission
};
