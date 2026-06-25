type Props = {
  status: string;
};

export default function StatusBadge({
  status,
}: Props) {
  let textColor = "";

  if (status === "Online") {
    textColor = "text-green-400";
  } else if (status === "Warning") {
    textColor = "text-yellow-400";
  } else {
    textColor = "text-red-400";
  }

  return (
    <span className={`font-medium ${textColor}`}>
      ● {status}
    </span>
  );
}