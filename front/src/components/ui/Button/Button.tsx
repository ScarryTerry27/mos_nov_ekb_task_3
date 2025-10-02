import {Button} from "react-native";
import {FC} from "react";

interface  ButtonProps {
  title: string;
  onPress: () => void;
}

const CustomButton : FC<ButtonProps> = (props) => {
  const {
    title,
    onPress,
  } = props;

  return (
    <Button title={title} onPress={onPress} />
  )
}

export { CustomButton as Button };