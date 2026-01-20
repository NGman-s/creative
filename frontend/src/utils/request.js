const BASE_URL = 'http://localhost:8000'; // Changed to localhost for local H5 development

const request = (options) => {
  return new Promise((resolve, reject) => {
    uni.request({
      url: BASE_URL + options.url,
      method: options.method || 'GET',
      data: options.data || {},
      header: options.header || {},
      timeout: options.timeout || 10000,
      success: (res) => {
        // Response Interceptor
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data);
        } else {
          uni.showToast({
            title: `错误: ${res.statusCode}`,
            icon: 'none'
          });
          reject(res);
        }
      },
      fail: (err) => {
        uni.showToast({
          title: '网络错误',
          icon: 'none'
        });
        reject(err);
      }
    });
  });
};

const uploadFile = (options) => {
  return new Promise((resolve, reject) => {
    uni.uploadFile({
      url: BASE_URL + options.url,
      filePath: options.filePath,
      name: options.name || 'file',
      formData: options.formData || {},
      header: options.header || {},
      timeout: options.timeout || 30000,
      success: (res) => {
        // Response Interceptor
        if (res.statusCode >= 200 && res.statusCode < 300) {
          try {
            const data = JSON.parse(res.data);
            resolve(data);
          } catch (e) {
            resolve(res.data);
          }
        } else {
          uni.showToast({
            title: `上传错误: ${res.statusCode}`,
            icon: 'none'
          });
          reject(res);
        }
      },
      fail: (err) => {
        uni.showToast({
          title: '上传失败',
          icon: 'none'
        });
        reject(err);
      }
    });
  });
};

export default {
  request,
  uploadFile
};
