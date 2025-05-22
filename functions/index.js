// functions/index.js
const functions = require('firebase-functions');
const admin = require('firebase-admin');
const cors = require('cors')({ origin: true });

// Initialize with detailed logging
console.log('Initializing Firebase Admin with config:', {
  projectId: 'agritech-pk',
  storageBucket: 'agritech-pk.firebasestorage.app'
});

// Initialize Firebase Admin with proper credentials
// The NOT_FOUND error typically occurs when Firebase can't find the project
// or doesn't have proper permissions
admin.initializeApp({
  storageBucket: 'agritech-pk.firebasestorage.app'
});

const db = admin.firestore();
const bucket = admin.storage().bucket();
console.log('Firebase services initialized');

// Function to detect MIME type from base64 string
function detectMimeType(base64String) {
  // Extract the first few characters to identify the image type
  const prefix = base64String.substr(0, 100);
  
  console.log('Detecting image format...');
  
  if (prefix.indexOf('iVBOR') === 0) {
    console.log('Detected PNG image');
    return { contentType: 'image/png', extension: 'png' };
  } else if (prefix.indexOf('/9j/') === 0) {
    console.log('Detected JPEG image');
    return { contentType: 'image/jpeg', extension: 'jpg' };
  } else if (prefix.indexOf('R0lGOD') === 0) {
    console.log('Detected GIF image');
    return { contentType: 'image/gif', extension: 'gif' };
  } else if (prefix.indexOf('UklGR') === 0) {
    console.log('Detected WEBP image');
    return { contentType: 'image/webp', extension: 'webp' };
  } else {
    console.log('Unknown image format, defaulting to JPEG');
    return { contentType: 'image/jpeg', extension: 'jpg' };
  }
}

exports.uploadVegetableData = functions.https.onRequest((req, res) => {
  console.log('Function invoked with method:', req.method);
  
  cors(req, res, async () => {
    if (req.method !== 'POST') {
      console.log('Invalid method:', req.method);
      return res.status(405).json({ error: 'Only POST allowed' });
    }
    
    try {
      console.log('Received request body keys:', Object.keys(req.body));
      
      const { imageBase64, weight, vegName, dateTime } = req.body;
      
      // Check required fields
      const missingFields = [];
      if (!imageBase64) missingFields.push('imageBase64');
      if (!weight) missingFields.push('weight');
      if (!vegName) missingFields.push('vegName');
      if (!dateTime) missingFields.push('dateTime');
      
      if (missingFields.length > 0) {
        console.log('Missing required fields:', missingFields);
        return res.status(400).json({ error: `Missing required fields: ${missingFields.join(', ')}` });
      }
      
      console.log(`Processing vegetable: ${vegName}, weight: ${weight}, dateTime: ${dateTime}`);
      console.log(`Image data received (length: ${imageBase64.length} chars)`);
      
      // Decode Base64 image
      try {
        var buffer = Buffer.from(imageBase64, 'base64');
        console.log(`Decoded image buffer (size: ${buffer.length} bytes)`);
      } catch (decodeErr) {
        console.error('Error decoding base64 image:', decodeErr);
        return res.status(400).json({ error: 'Invalid base64 image data' });
      }
      
      // Detect image format and get proper content type and extension
      const { contentType, extension } = detectMimeType(imageBase64);
      
      // Create a unique filename with the proper extension
      const timestamp = Date.now();
      const fileName = `vegetables/${vegName.replace(/\s+/g,'_')}_${timestamp}.${extension}`;
      console.log(`Creating file: ${fileName} with contentType: ${contentType}`);
      
      // Use the bucket instance directly instead of recreating it
      console.log('Starting upload to Storage...');
      try {
        await bucket.file(fileName).save(buffer, {
          metadata: { contentType: contentType },
          public: true,
          validation: 'md5'
        });
        console.log('File successfully uploaded to Storage');
      } catch (storageErr) {
        console.error('Error uploading to Storage:', storageErr);
        return res.status(500).json({ error: `Storage error: ${storageErr.message}` });
      }
      
      // Construct public URL
      const imageUrl = `https://storage.googleapis.com/${bucket.name}/${fileName}`;
      console.log(`Generated image URL: ${imageUrl}`);
      
      // Parse dateTime and convert to Firestore Timestamp
      console.log(`Parsing dateTime: ${dateTime}`);
      const parsedDate = new Date(dateTime);
      if (isNaN(parsedDate.getTime())) {
        console.error('Invalid date format:', dateTime);
        return res.status(400).json({ error: 'Invalid dateTime format' });
      }
      
      const ts = admin.firestore.Timestamp.fromDate(parsedDate);
      console.log(`Converted to Firestore timestamp: ${ts.toDate().toISOString()}`);
      
      // Verify Firestore connection before attempting to write
      console.log('Checking Firestore connection...');
      try {
        await db.collection('vegetables').doc('test-connection').set({ test: true }, { merge: true });
        console.log('Firestore connection verified');
      } catch (connectionErr) {
        console.error('Firestore connection test failed:', connectionErr);
        console.error('Error code:', connectionErr.code);
        console.error('Error message:', connectionErr.message);
        return res.status(500).json({ 
          error: `Firestore connection error: ${connectionErr.message}`,
          code: connectionErr.code || 'UNKNOWN'
        });
      }
      
      // Save document to Firestore
      console.log('Preparing Firestore document...');
      const vegetableData = {
        imageUrl,
        weight: parseFloat(weight), // Ensure weight is a number
        vegName: String(vegName),   // Ensure vegName is a string
        dateTime: ts,
        uploadedAt: admin.firestore.FieldValue.serverTimestamp()
      };
      
      console.log('Saving document to Firestore collection "vegetables"...');
      let docRef;
      try {
        // Add more detailed error logging
        console.log('Document data to be saved:', JSON.stringify(vegetableData, (key, value) => 
          value instanceof admin.firestore.Timestamp ? value.toDate().toISOString() : value
        ));
        
        docRef = await db.collection('vegetables').add(vegetableData);
        console.log(`Document successfully saved with ID: ${docRef.id}`);
      } catch (firestoreErr) {
        console.error('Firestore error details:', firestoreErr);
        console.error('Firestore error code:', firestoreErr.code);
        console.error('Firestore error message:', firestoreErr.message);
        console.error('Firestore error stack:', firestoreErr.stack);
        
        // More specific error handling for NOT_FOUND error
        if (firestoreErr.code === 5 || firestoreErr.message.includes('NOT_FOUND')) {
          console.error('NOT_FOUND error detected. This typically means the Firestore database does not exist or the service account lacks permissions.');
          return res.status(500).json({
            error: 'Database configuration error. Please check that your Firestore database exists and service account has proper permissions.',
            code: 'NOT_FOUND'
          });
        }
        
        return res.status(500).json({ 
          error: `Firestore error: ${firestoreErr.message}`,
          code: firestoreErr.code || 'UNKNOWN'
        });
      }
      
      console.log('Operation completed successfully');
      return res.status(200).json({
        message: 'Upload successful',
        id: docRef.id,
        data: { 
          imageUrl, 
          weight, 
          vegName, 
          dateTime: parsedDate.toISOString(),
          format: contentType
        }
      });
    } catch (err) {
      console.error('FATAL ERROR in uploadVegetableData:', err);
      console.error('Error stack:', err.stack);
      return res.status(500).json({ 
        error: err.message,
        stack: err.stack,
        code: err.code || 'UNKNOWN'
      });
    }
  });
});