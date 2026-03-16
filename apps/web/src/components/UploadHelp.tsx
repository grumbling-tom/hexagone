interface UploadHelpProps {
  className?: string;
}

export default function UploadHelp({ className = "" }: UploadHelpProps) {
  const bemClass = "upload-help";
  const fullClass = className ? `${bemClass} ${className}` : bemClass;

  return (
    <div className={fullClass}>
      <details className="upload-help__accordion">
        <summary className="upload-help__summary">What is a GPX file?</summary>
        <p className="upload-help__text">
          A GPX file (GPS Exchange Format) is a standard format for storing GPS
          data. It is commonly used for sharing and analyzing outdoor activities
          like running, cycling, and hiking.
        </p>
      </details>
      <details className="upload-help__accordion">
        <summary className="upload-help__summary">
          Where can I find this?
        </summary>
        <p className="upload-help__text">
          Export GPX files from fitness apps like Strava, Garmin Connect, or
          similar platforms.
        </p>
      </details>
    </div>
  );
}
