import logging
from typing import Dict, Any, Optional
from json_logic import jsonLogic

from app.engine.graph.graph_event import EventType, GraphEvent
from app.engine.interfaces.i_processor import IProcessor

logger = logging.getLogger(__name__)


class SwitchProcessor(IProcessor):
    """
    Switch processor that routes events based on JsonLogic rules.
    
    Config format:
    {
        "rules": [
            {
                "rule-1": {
                    "condition": {">": [{"var": "value.second"}, 5]},
                    "then": "to-send_notification"
                }
            },
            {
                "rule-2": {
                    "condition": {"==": [{"var": "user.status"}, "active"]},
                    "then": "to-active_users"
                }
            }
        ],
        "default_target": "to-default_handler"
    }
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.rules = config.get("rules", [])
        self.default_target = config.get("default_target", None)
        
    def can_handle(self, event: GraphEvent) -> bool:
        """Can handle any event type"""
        return True
        
    async def process(self, event: GraphEvent, context: Dict[str, Any]) -> Optional[GraphEvent]:
        """
        Process the event and route it based on matching JsonLogic rules.
        
        Args:
            event: The incoming event
            context: Processing context containing node_id
            
        Returns:
            GraphEvent with routing information or None if no rules match
        """
        try:
            # Evaluate all rules against the event data
            matched_rule = self._evaluate_rules(event.data)
            
            if matched_rule:
                logger.info(f"Rule matched: {matched_rule['rule_name']} -> {matched_rule['target']}")
                return self._create_routing_event(event, matched_rule, context["node_id"])
            elif self.default_target:
                logger.info(f"No rules matched, using default target: {self.default_target}")
                return self._create_routing_event(event, {"target": self.default_target}, context["node_id"])
            else:
                logger.warning("No rules matched and no default target specified")
                return self._create_no_match_event(event, context["node_id"])
                
        except Exception as e:
            logger.error(f"Error processing JsonLogic rules: {str(e)}")
            return self._create_error_event(f"JsonLogic processing error: {str(e)}", event, context["node_id"])
    
    def _evaluate_rules(self, data: Any) -> Optional[Dict[str, Any]]:
        """
        Evaluate all JsonLogic rules against the given data.
        
        Args:
            data: The data to evaluate against
            
        Returns:
            Dict with rule information if matched, None otherwise
        """
        for rule_group in self.rules:
            for rule_name, rule_config in rule_group.items():
                try:
                    if self._evaluate_single_rule(data, rule_config):
                        return {
                            "rule_name": rule_name,
                            "target": rule_config.get("then"),
                            "condition": rule_config.get("condition")
                        }
                except Exception as e:
                    logger.debug(f"Error evaluating JsonLogic rule {rule_name}: {str(e)}")
                    continue
        return None
    
    def _evaluate_single_rule(self, data: Any, rule_config: Dict[str, Any]) -> bool:
        """
        Evaluate a single JsonLogic rule against the data.
        
        Args:
            data: The data to evaluate
            rule_config: The rule configuration with JsonLogic condition
            
        Returns:
            True if rule matches, False otherwise
        """
        condition = rule_config.get("condition")
        if not condition:
            return False
            
        try:
            # JsonLogic evaluates the condition against the data directly
            result = jsonLogic(condition, data)
            return bool(result)
        except Exception as e:
            logger.debug(f"JsonLogic evaluation failed: {str(e)}")
            return False
    
    def _create_routing_event(self, original_event: GraphEvent, rule_info: Dict[str, Any], node_id: str) -> GraphEvent:
        """
        Create a routing event with target information.
        
        Args:
            original_event: The original event
            rule_info: Information about the matched rule
            node_id: The switch node ID
            
        Returns:
            GraphEvent with routing data
        """
        return GraphEvent(
            type=EventType.ROUTING_DECISION,
            data={
                "original_data": original_event.data,
                "target_node": rule_info.get("target"),
                "rule_name": rule_info.get("rule_name"),
                "condition": rule_info.get("condition"),
                "routing_type": "jsonlogic_switch"
            },
            source_id=node_id,
            metadata={
                "status": "routed",
                "target": rule_info.get("target"),
                **original_event.metadata
            }
        )
    
    def _create_no_match_event(self, original_event: GraphEvent, node_id: str) -> GraphEvent:
        """
        Create an event when no rules match.
        
        Args:
            original_event: The original event
            node_id: The switch node ID
            
        Returns:
            GraphEvent indicating no match
        """
        return GraphEvent(
            type=EventType.ROUTING_DECISION,
            data={
                "original_data": original_event.data,
                "target_node": None,
                "routing_type": "jsonlogic_switch",
                "status": "no_match"
            },
            source_id=node_id,
            metadata={
                "status": "no_match",
                **original_event.metadata
            }
        )
    
    def _create_error_event(self, error_message: str, original_event: GraphEvent, node_id: str) -> GraphEvent:
        """
        Create an error event.
        
        Args:
            error_message: The error message
            original_event: The original event
            node_id: The switch node ID
            
        Returns:
            GraphEvent with error information
        """
        return GraphEvent(
            type=EventType.ERROR,
            data={
                "error": error_message,
                "original_data": original_event.data,
                "routing_type": "jsonlogic_switch"
            },
            source_id=node_id,
            metadata={
                "status": "error",
                **original_event.metadata
            }
        )