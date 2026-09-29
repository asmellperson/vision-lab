"""Execute exported teaching examples on synthetic images, without platform imports."""
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile

import cv2
import numpy as np

examples = json.loads(Path(sys.argv[1]).read_text())
cv2.setNumThreads(2)
rng = np.random.default_rng(7)
image = rng.integers(0, 120, (160, 200, 3), dtype=np.uint8)
cv2.rectangle(image, (35, 35), (160, 120), (180, 220, 240), -1)
cv2.circle(image, (90, 80), 20, (15, 25, 30), -1)
ids = '''pixels gray color rgb hsv lab ycrcb channel merge add subtract blend bit_and bit_or bit_xor bit_not
histogram brightness gamma equalize clahe mean gaussian median bilateral nlm convolution sharpen fft lowpass highpass
threshold adaptive otsu erode dilate open close morph_gradient tophat blackhat skeleton distance sobel scharr laplacian canny
contours components hull shape_match contour_area contour_perimeter centroid bounding_box hough_lines hough_circles
resize rotate affine kmeans_segment watershed harris shi sift orb hog lbp knn svm kmeans_demo lowlight augmentation qr barcode
eval_classification eval_detection eval_segmentation difference color_check defects'''.split()
failures, passed = [], []
with tempfile.TemporaryDirectory(prefix='vision-python-') as folder:
    os.chdir(folder)
    cv2.imwrite('input.jpg', image)
    cv2.imwrite('reference.jpg', image)
    cv2.imwrite('truth.png', cv2.cvtColor(image, cv2.COLOR_BGR2GRAY))
    cv2.imwrite('prediction.png', cv2.cvtColor(image, cv2.COLOR_BGR2GRAY))
    for name in ids:
        if name not in examples:
            failures.append(name + ': missing example')
            continue
        cv2.setRNGSeed(42)
        namespace = {'__name__': '__main__'}
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                exec(compile(examples[name], name + '.py', 'exec'), namespace)
            if name in {'canny', 'gray', 'threshold', 'erode', 'dilate', 'open', 'close', 'bit_not'}:
                source, params = namespace['image'], namespace['params']
                gray = cv2.cvtColor(source, cv2.COLOR_BGR2GRAY)
                if name == 'canny':
                    expected = cv2.Canny(gray, params['low'], params['high'])
                elif name == 'gray':
                    expected = gray
                elif name == 'threshold':
                    expected = cv2.threshold(gray, params['threshold'], 255, cv2.THRESH_BINARY)[1]
                elif name == 'bit_not':
                    expected = 255 - source
                else:
                    # The page applies morphology to the original channels, not an implicit threshold.
                    expected = cv2.morphologyEx(source, {'erode': cv2.MORPH_ERODE, 'dilate': cv2.MORPH_DILATE, 'open': cv2.MORPH_OPEN, 'close': cv2.MORPH_CLOSE}[name], namespace['kernel'], iterations=int(params['iterations']))
                np.testing.assert_array_equal(namespace['output'], expected, err_msg=name)
            passed.append(name)
        except Exception as error:
            failures.append(f'{name}: {type(error).__name__}: {error}')
    print(json.dumps({'executed': len(passed), 'passed': passed, 'failures': failures}, ensure_ascii=False))
    if failures:
        raise SystemExit(1)
