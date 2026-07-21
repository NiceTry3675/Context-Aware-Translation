export default function ServiceClosedPage() {
  return (
    <main className="closure-page">
      <section className="closure-content" aria-labelledby="closure-title">
        <div className="closure-brand" aria-label="냥번역">
          <span className="closure-brand-mark" aria-hidden="true">냥</span>
          <span>냥번역</span>
        </div>

        <div className="closure-status">
          <span className="closure-status-dot" aria-hidden="true" />
          서비스 종료
        </div>

        <h1 id="closure-title">서비스 운영을 종료했습니다.</h1>
        <p className="closure-lead">
          냥번역은 2026년 7월 21일부로 번역 서비스 운영을 종료했습니다.
        </p>
        <p className="closure-description">
          번역 작업 생성과 기존 작업 조회, 결과 다운로드 기능은 더 이상 제공되지 않습니다.
        </p>

        <dl className="closure-details">
          <div>
            <dt>운영 종료일</dt>
            <dd>2026. 07. 21.</dd>
          </div>
          <div>
            <dt>서비스 상태</dt>
            <dd>모든 기능 종료</dd>
          </div>
        </dl>

        <p className="closure-thanks">
          그동안 냥번역을 이용해 주셔서 감사합니다.
        </p>
      </section>
    </main>
  );
}
