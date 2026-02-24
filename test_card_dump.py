import json
from yoto_up.models import Card, CardContent, CardMetadata, CardMedia, Chapter

card_media = CardMedia(duration=100, fileSize=2000, readableDuration="1m 0s", readableFileSize=1.5, hasStreams=False)
card_meta = CardMetadata(media=card_media)
card = Card(title="Test", content=CardContent(chapters=[]), metadata=card_meta)

data = card.model_dump(exclude_none=True)
print(json.dumps(data, indent=2))
