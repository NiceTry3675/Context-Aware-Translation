def update_job_state(db: Session, job_id: int, segment_index: int, glossary: dict, styles: dict):
    db_job = get_job(db, job_id)
    if db_job:
        db_job.last_successful_segment = segment_index
        
        context_snapshot = {
            "glossary": glossary,
            "character_styles": styles
        }
        db_job.context_snapshot_json = json.dumps(context_snapshot, ensure_ascii=False)
        
        db.commit()
        db.refresh(db_job)
    return db_job