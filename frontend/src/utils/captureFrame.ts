/**
 * Capture a single JPEG frame from the user's local browser webcam.
 * Returns a base64-encoded JPEG string (no "data:image/jpeg;base64," prefix).
 */
export async function captureFrameFromCamera(): Promise<string> {
  const stream = await navigator.mediaDevices.getUserMedia({
    video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: 'user' },
  });

  const video = document.createElement('video');
  video.srcObject = stream;
  video.muted = true;

  await new Promise<void>((resolve) => {
    video.onloadedmetadata = () => resolve();
  });
  await video.play();

  // Give the camera ~400ms to adjust exposure/focus
  await new Promise((r) => setTimeout(r, 400));

  const canvas = document.createElement('canvas');
  canvas.width = video.videoWidth || 640;
  canvas.height = video.videoHeight || 480;
  canvas.getContext('2d')!.drawImage(video, 0, 0);

  // Stop all tracks immediately to release the camera
  stream.getTracks().forEach((t) => t.stop());

  // Return raw base64 (strip the "data:image/jpeg;base64," prefix)
  const dataUrl = canvas.toDataURL('image/jpeg', 0.92);
  return dataUrl.split(',')[1];
}
