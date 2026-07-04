from sqlalchemy import Column, Integer, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy import func
from app.database import Base


class NoticeRead(Base):
    __tablename__ = "notice_reads"

    id = Column(Integer, primary_key=True)

    notice_id = Column(
        Integer,
        ForeignKey("notices.id", ondelete="CASCADE"),
        nullable=False,
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    read_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "notice_id",
            "user_id",
            name="uq_notice_read_user",
        ),
    )



