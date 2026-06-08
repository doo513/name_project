for result in results:
    if result.boxes is None:
        continue

    boxes = result.boxes.xyxy.cpu().numpy()
    scores = result.boxes.conf.cpu().numpy()
    classes = result.boxes.cls.cpu().numpy()

    h, w, _ = img.shape

    for box, score, cls in zip(boxes, scores, classes):
        if score < 0.5:
            continue

        x1, y1, x2, y2 = map(int, box)

        # 좌표 보정
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)

        crop = img[y1:y2, x1:x2]

        # 전처리
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)

        ocr_result = reader.readtext(gray)

        for (_, text, prob) in ocr_result:
            if prob > 0.5:
                cv2.putText(img, text, (x1, y1-10),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.5, (0,255,0), 2)

        cv2.rectangle(img, (x1, y1), (x2, y2), (0,255,0), 2)
