import Api from './Api'
function generateUploadToken() {
  // Generate a unique token using a combination of timestamp and random characters
  const timestamp = Date.now();
  const randomChars = Math.random().toString(36).substr(2, 8);
  const uploadToken = `${timestamp}_${randomChars}`;

  return uploadToken;
}
const service = {
  getVideos(sort) {
    return Api().get('/api/videos', {
      params: {
        sort,
      },
    })
  },
  getPublicVideos(sort) {
    return Api().get('/api/videos/public', {
      params: {
        sort,
      },
    })
  },
  getDetails(id) {
    return Api().get(`/api/video/details/${id}`)
  },
  getRandomVideo() {
    return Api().get('/api/video/random')
  },
  getRandomPublicVideo() {
    return Api().get('/api/video/public/random')
  },
  getViews(id) {
    return Api().get(`/api/video/${id}/views`)
  },
  updateTitle(id, title) {
    return Api().put(`/api/video/details/${id}`, {
      title,
    })
  },
  updatePrivacy(id, value) {
    return Api().put(`/api/video/details/${id}`, {
      private: value,
    })
  },
  updateDetails(id, details) {
    return Api().put(`/api/video/details/${id}`, {
      ...details,
    })
  },
  addView(id) {
    return Api().post(`/api/video/view`, {
      video_id: id,
    })
  },
  delete(id) {
    return Api().delete(`/api/video/delete/${id}`)
  },
  upload(inputformData, uploadProgress) {
    console.log("uploading");
    const file = inputformData.get('file');
    const FileName = file.name;
    const chunkSize = 95 * 1024 * 1024; // 10MB chunk size (adjust as needed)
    const fileSize = file.size;
    const totalChunks = Math.ceil(fileSize / chunkSize);
    const uploadToken = generateUploadToken(); // Function to generate a unique upload token

    console.log(`upload: filename:${FileName} ,chunksize:${chunkSize}, fileSize:${fileSize}, totalChunks:${totalChunks}, uploadToken:${uploadToken}  `);
    const uploadChunk = (chunkNumber) => {
      return new Promise((resolve, reject) => {
        console.log(`upload: uploadChunk ${chunkNumber}`);
        const start = chunkNumber * chunkSize;
        const end = Math.min(start + chunkSize, fileSize);
        const chunk = file.slice(start, end);
  
        const formData = new FormData();
        formData.append('file', chunk);
        formData.append('uploadToken', uploadToken);
        formData.append('chunkNumber', chunkNumber);
        formData.append('totalChunks', totalChunks);
        formData.append('OGFileName', FileName);
        console.log(`upload: api`);
        Api()
          .post('/api/upload', formData, {
            timeout: 999999999,
            headers: {
              'Content-Type': 'multipart/form-data',
            },
            
            onUploadProgress: (progressEvent) => {
              console.log(`upload: onUploadProgress  `);
              const progress = (start + progressEvent.loaded) / fileSize;
              uploadProgress(progress, {
                loaded: (start + progressEvent.loaded) / Math.pow(10, 6),
                total: fileSize / Math.pow(10, 6),
              });
            },
          })
          .then(() => {
            resolve();
          })
          .catch((error) => {
            console.log(`upload: api error ${error} `);
            reject(error);
          });
      });
    };
  
    const uploadChunks = async () => {
      for (let chunkNumber = 0; chunkNumber < totalChunks; chunkNumber++) {
        await uploadChunk(chunkNumber);
      }
    };
    return uploadChunks();
  },
  
  publicUpload(inputformData, uploadProgress) {
    console.log("uploading");
    const file = inputformData.get('file');
    const FileName = file.name;
    const chunkSize = 95 * 1024 * 1024; // 10MB chunk size (adjust as needed)
    const fileSize = file.size;
    const totalChunks = Math.ceil(fileSize / chunkSize);
    const uploadToken = generateUploadToken(); // Function to generate a unique upload token

    console.log(`upload: filename:${FileName} ,chunksize:${chunkSize}, fileSize:${fileSize}, totalChunks:${totalChunks}, uploadToken:${uploadToken}  `);
    const uploadChunk = (chunkNumber) => {
      return new Promise((resolve, reject) => {
        console.log(`upload: uploadChunk ${chunkNumber}`);
        const start = chunkNumber * chunkSize;
        const end = Math.min(start + chunkSize, fileSize);
        const chunk = file.slice(start, end);
  
        const formData = new FormData();
        formData.append('file', chunk);
        formData.append('uploadToken', uploadToken);
        formData.append('chunkNumber', chunkNumber);
        formData.append('totalChunks', totalChunks);
        formData.append('OGFileName', FileName);
        console.log(`upload: api`);
        Api()
          .post('/api/upload/public', formData, {
            timeout: 999999999,
            headers: {
              'Content-Type': 'multipart/form-data',
            },
            
            onUploadProgress: (progressEvent) => {
              console.log(`upload: onUploadProgress  `);
              const progress = (start + progressEvent.loaded) / fileSize;
              uploadProgress(progress, {
                loaded: (start + progressEvent.loaded) / Math.pow(10, 6),
                total: fileSize / Math.pow(10, 6),
              });
            },
          })
          .then(() => {
            resolve();
          })
          .catch((error) => {
            console.log(`upload: api error ${error} `);
            reject(error);
          });
      });
    };
  
    const uploadChunks = async () => {
      for (let chunkNumber = 0; chunkNumber < totalChunks; chunkNumber++) {
        await uploadChunk(chunkNumber);
      }
    };
    return uploadChunks();
  },
  scan() {
    return Api().get('/api/manual/scan')
  },
}

export default service
