"""Models do domínio. Importar daqui garante o registro no metadata do SQLAlchemy."""
from app.models.base import Base
from app.models.caption import Caption
from app.models.job import Job, JobStatus
from app.models.profile import Profile
from app.models.video import Video

__all__ = ["Base", "Profile", "Video", "Caption", "Job", "JobStatus"]
